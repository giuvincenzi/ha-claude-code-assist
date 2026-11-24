---
paths:
  - "ha_claude_code_assist/core/ha_cca/prompt.py"
  - "ha_claude_code_assist/core/ha_cca/config.py"
  - "ha_claude_code_assist/core/ha_cca/mcp_tools.py"
  - "ha_claude_code_assist/core/ha_cca/app_info.py"
---

# System prompt and internal tools

The system prompt Claude gets in every session and the internal tools (`ha_cca_*`).

- The prompt holds only what does not change: identity, personality, behaviour. Its only
  variable parts are the channel (fixed for the conversation), the sections the user rewrites and
  the memory sections (only when memory is on). Anything that changes more often breaks the
  prompt cache.
- There is one prompt per channel. The user rewrites its sections (`SECTIONS`) in Settings >
  Agent, kept in the options `prompt_<channel>_<section>`; a blank one, or one equal to its
  default, is saved empty (`normalize_prompt`), so a later version's default reaches it.
- What the app needs to work (tools, `ha_cca_app_info`, reading the real state, the context tag)
  is in `SYSTEM`, never in a section the user can rewrite (`test_prompt.py` checks).
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
