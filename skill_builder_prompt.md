# Skill Builder Prompt

Use this to offload skill scaffolding to a sub-agent.

---

**Task:** Draft a complete skill structure for OpenClaw

**Model:** Use a small/frugal model (qwen-3.5 or glm-5 via Ollama Cloud)

**Timeout:** 60 seconds max

**Input:** The human will provide:
- Skill name
- Brief description of what it should do
- Any specific commands or APIs it needs

**Your output should be:**
A complete skill folder structure in `/home/sntrblck/.openclaw/workspace/skills/<skill_name>/` containing:

1. **SKILL.md** — The main skill file with:
   - Description
   - Commands (CLI format: `python3 skill_file.py <command> [args]`)
   - Parameters and their types
   - Integration notes (how it fits with other skills, memory, cron)
   - Usage examples

2. **`<skill_name>.py`** — The main Python script with:
   - CLI argument parsing
   - Core logic functions
   - Error handling
   - Logging output

3. **Setup notes** — Any dependencies, API keys, or configuration needed

**Constraints:**
- Output ONLY valid Python and Markdown
- No markdown code blocks wrapping the file content
- Functions should be modular and testable
- Include docstrings
- Keep it simple — don't over-engineer

**Example input they'd send:**
```
Skill: price-checker
Description: Monitor token prices and alert on threshold breaches
Commands: check <token_address>, set-alert <token> <threshold>
```

**Deliverable:** Write files directly to the skills directory. Report what was created.