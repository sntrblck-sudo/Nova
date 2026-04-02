/**
 * Helper functions for the Base Token Price & Listing Alert skill.
 * Uses DEXScreener API (no API key required).
 */

const DEX_SCREENER_API = "https://api.dexscreener.com/latest/dex/tokens";

/**
 * Fetches token price and listing status from DEXScreener.
 * @param {string} tokenAddress - The ERC20 token address on Base.
 * @returns {Promise<Object>} Object containing isListed, priceUsd, dex, pairAddress, liquidity.
 */
export async function getTokenData(tokenAddress) {
  try {
    const response = await fetch(`${DEX_SCREENER_API}/${tokenAddress}`);
    const data = await response.json();

    // Filter for Base network pairs
    const basePairs = data.pairs?.filter(pair => pair.chainId === 'base') || [];

    if (basePairs.length === 0) {
      return {
        isListed: false,
        priceUsd: 0,
        message: "unlisted"
      };
    }

    // Sort by liquidity for most reliable price
    const primaryPair = basePairs.sort((a, b) => b.liquidity.usd - a.liquidity.usd)[0];

    return {
      isListed: true,
      priceUsd: parseFloat(primaryPair.priceUsd),
      dex: primaryPair.dexId,
      pairAddress: primaryPair.pairAddress,
      liquidity: primaryPair.liquidity.usd
    };

  } catch (error) {
    console.error(`Error fetching data from DEXScreener: ${error.message}`);
    throw new Error("Failed to fetch token data");
  }
}