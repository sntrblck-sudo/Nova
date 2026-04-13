// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title TipVault
/// @notice Nova's AI-to-AI tipping contract on Base
/// @dev Nova funds the vault, then sends tips to other AI agents from it.
contract TipVault {
    // --- Immutable config ---
    address public immutable OWNER;
    uint256 public constant MIN_TIP = 0.0001 ether;   // 0.1 finney
    uint256 public constant MAX_TIP = 0.005 ether;     // 5 finney
    uint256 public constant COOLDOWN = 1 hours;

    // --- State ---
    uint256 public totalTipped;
    uint256 public tipCount;

    mapping(address => uint256) public lastTipTimestamp;
    mapping(address => uint256) public tipCountPerRecipient;

    // --- Events ---
    event Tipped(
        address indexed from,
        address indexed to,
        uint256 amount,
        string reason
    );
    event Withdrawn(address indexed to, uint256 amount);
    event Received(address indexed from, uint256 amount);

    // --- Modifiers ---
    modifier onlyOwner() {
        require(msg.sender == OWNER, "UNAUTHORIZED");
        _;
    }

    // --- Core ---
    constructor(address owner) {
        require(owner != address(0), "ZERO_OWNER");
        OWNER = owner;
    }

    /// @notice Send a tip from the vault to a recipient
    /// @param to     Recipient's Base wallet address
    /// @param amount  Tip amount in wei
    /// @param reason  Off-chain context (Bluesky URI, conversation summary)
    function tip(address payable to, uint256 amount, string calldata reason)
        external
        onlyOwner
    {
        _tip(to, amount, reason);
    }

    /// @notice Batch tip multiple recipients in one transaction
    /// @param recipients  Array of recipient addresses
    /// @param amounts     Array of tip amounts (wei)
    /// @param reasons     Array of off-chain reasons
    function batchTip(
        address[] calldata recipients,
        uint256[] calldata amounts,
        string[] calldata reasons
    ) external onlyOwner {
        require(recipients.length == amounts.length, "LENGTH_MISMATCH");
        require(recipients.length == reasons.length, "LENGTH_MISMATCH");

        for (uint256 i = 0; i < recipients.length; i++) {
            _tip(payable(recipients[i]), amounts[i], reasons[i]);
        }
    }

    function _tip(address payable to, uint256 amount, string calldata reason)
        internal
    {
        require(to != address(0), "ZERO_RECIPIENT");
        require(to != OWNER, "NO_SELF_TIP");
        require(amount >= MIN_TIP, "BELOW_MIN");
        require(amount <= MAX_TIP, "ABOVE_MAX");
        require(address(this).balance >= amount, "INSUFFICIENT_BALANCE");

        // Cooldown
        uint256 remaining = _cooldownRemaining(to);
        require(remaining == 0, "COOLDOWN_ACTIVE");

        lastTipTimestamp[to] = block.timestamp;
        tipCountPerRecipient[to]++;
        totalTipped += amount;
        tipCount++;

        (bool sent, ) = to.call{value: amount}("");
        require(sent, "TRANSFER_FAILED");

        emit Tipped(OWNER, to, amount, reason);
    }

    // --- Admin ---
    function withdraw() external onlyOwner {
        uint256 bal = address(this).balance;
        require(bal > 0, "ZERO_BALANCE");
        (bool sent, ) = OWNER.call{value: bal}("");
        require(sent, "TRANSFER_FAILED");
        emit Withdrawn(OWNER, bal);
    }

    function withdrawAmount(uint256 amount) external onlyOwner {
        require(amount <= address(this).balance, "INSUFFICIENT_BALANCE");
        (bool sent, ) = OWNER.call{value: amount}("");
        require(sent, "TRANSFER_FAILED");
        emit Withdrawn(OWNER, amount);
    }

    /// @notice Top up the vault
    receive() external payable {
        emit Received(msg.sender, msg.value);
    }

    // --- Views ---
    function _cooldownRemaining(address recipient)
        internal
        view
        returns (uint256)
    {
        if (lastTipTimestamp[recipient] == 0) return 0;
        uint256 elapsed = block.timestamp - lastTipTimestamp[recipient];
        return elapsed >= COOLDOWN ? 0 : COOLDOWN - elapsed;
    }

    function getCooldownRemaining(address recipient)
        external
        view
        returns (uint256)
    {
        return _cooldownRemaining(recipient);
    }

    function getTipStats(address recipient)
        external
        view
        returns (uint256 count, uint256 lastTimestamp)
    {
        return (tipCountPerRecipient[recipient], lastTipTimestamp[recipient]);
    }

    function getVaultBalance() external view returns (uint256) {
        return address(this).balance;
    }
}
