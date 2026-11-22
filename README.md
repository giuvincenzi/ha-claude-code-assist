<p align="center"><img src="ha_claude_code_assist/icon.png" width="96" height="96" alt=""></p>
<h1 align="center">HA Claude Code Assist</h1>
<p align="center"><i>A personal assistant for your home in Home Assistant, running Claude Code on your own Claude subscription.</i></p>
<p align="center">
  <a href="LICENSE"><img src="https://badgen.net/badge/license/MIT/blue" alt="MIT license"></a>
</p>
<p align="center">
  <a href="https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fgiuvincenzi%2Fha-claude-code-assist"><img src="https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg" alt="Add the HA Claude Code Assist repository to your Home Assistant app store."></a>
  <a href="https://my.home-assistant.io/redirect/marketplace_repository/?owner=giuvincenzi&repository=ha-claude-code-assist&category=integration"><img src="https://my.home-assistant.io/badges/marketplace_repository.svg" alt="Open the HA Claude Code Assist integration in your Home Assistant Marketplace."></a>
</p>

HA Claude Code Assist brings Claude Code into Home Assistant as a personal assistant for your
home, running on your own Claude subscription. You talk to it in a chat in Home Assistant, or
by voice through Home Assistant Assist. It answers about anything you ask, and acts only
through the tools you give it, such as Home Assistant's own MCP Server.

Unofficial project, not affiliated with, sponsored or endorsed by Anthropic. Claude and Claude
Code are trademarks of Anthropic.

## Documentation

[Documentation](ha_claude_code_assist/DOCS.md): installation, settings and how to give the
assistant its tools.

## Feedback

Found a bug or have an idea? [Open an issue](../../issues/new).

## Development

See [.claude/rules/](.claude/rules/).

## License

[MIT](LICENSE). Claude Code is not part of this repository: the app installs it from Anthropic
when it is built, under Anthropic's own terms.
