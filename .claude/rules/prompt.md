---
paths:
  - "ha_claude_code_assist/core/ha_cca/prompt.py"
  - "ha_claude_code_assist/core/ha_cca/mcp_tools.py"
  - "ha_claude_code_assist/core/ha_cca/app_info.py"
---

# System prompt and internal tools

The system prompt Claude gets in every session and the internal tools (`ha_cca_*`).

- The prompt holds only what does not change: identity, personality, behaviour. Its only
  variable parts are the channel (fixed for the conversation) and the memory sections (only when
  memory is on). Anything that changes more often breaks the prompt cache.
- Facts about the app never go in the prompt: they are in `DOCS.md`, which `ha_cca_app_info`
  returns with the current state appended. The prompt only says to call it.
- Rules in the prompt say why when it matters, in calm words: no capitals or "never" for
  emphasis, which make recent models over-apply them.
- Confirmation is asked only before deleting things or changing configuration: the prompt names
  no device types.
- Each extra tool call adds about a second: a rule that makes Claude call tools more often needs
  a reason worth that cost.
- A change to the prompt or to a tool description is checked with real conversations
  (`testing.md`) before it is kept.
