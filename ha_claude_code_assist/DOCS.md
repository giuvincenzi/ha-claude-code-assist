# HA Claude Code Assist

HA Claude Code Assist brings Claude Code into Home Assistant as a personal assistant for your
home, running on your own Claude subscription. You talk to it in a chat in Home Assistant, or
by voice through Home Assistant Assist. It answers about anything you ask, and acts only
through the tools you give it, such as Home Assistant's own MCP Server.

Unofficial project, not affiliated with, sponsored or endorsed by Anthropic. Claude and Claude
Code are trademarks of Anthropic.

Claude Code is Anthropic's official command-line tool. With a setup token from your
subscription it uses your plan's usage instead of pay-per-use API billing. The chat is in the
HA Claude Code Assist panel, in the Home Assistant sidebar (see
[Getting started](#getting-started) to show it), and the assistant remembers what you ask it to.

## Getting started

1. Add this repository to the app store with this button, then install the app and start it.

   [![Add the HA Claude Code Assist repository to your Home Assistant app store.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fgiuvincenzi%2Fha-claude-code-assist)

2. On the app's page (**Settings** > **Apps** > **HA Claude Code Assist**), turn on
   **Show in sidebar**. The HA Claude Code Assist panel appears in the Home Assistant sidebar.
   **Open Web UI**, on the same page, opens it too.
3. Create a setup token. On a computer where Claude Code is logged in with your Claude
   account, run `claude setup-token` in a terminal and copy the token it prints. A paid Claude
   plan is required (Pro, Max, Team or Enterprise). The token is valid for one year.
4. Open the HA Claude Code Assist panel, go to **Settings** > **Claude Code**, paste the token
   in **Setup token** and select **Save**.
5. Give the assistant its tools for your home (see [Tools](#tools)).
6. To talk to it by voice, set up Assist (see [Voice](#voice)).

## The panel

- **Chat** is where you talk to the assistant. Answers appear as they are written, and each
  tool it uses is shown on a line you can open to see what it sent and received. Under the
  message box you see the model, the effort and how much of the session's context is used.
  **New session** starts a new session right away. You can attach images, PDFs and text files
  to a message (see [Attachments](#attachments)).
- **Memory** lists what the assistant remembers across sessions.
- **Tools** holds the built-in tools, such as web search, and the MCP servers (see [Tools](#tools)).
- **Sessions** lists every session, active or ended. Select one to see its settings and what
  Claude Code reports about it (its own session ID, context, tokens used, cache, web searches)
  in **Info**, and its messages in **Messages**. **End session** ends an active session. **Delete** removes a session
  and all its messages for good, without touching long-term memory.
- **Settings** holds the setup token, the model and the effort in **Claude Code**, the timeout
  in **Sessions** and the long-term memory in **Memory**.

At the top, the panel shows whether the setup token is set, how many MCP servers are
configured and how many sessions are active. The setup token turns red when it is missing,
rejected or expired, and orange in the 30 days before it expires.

## Sessions

- A session starts with your first message and goes on while you keep writing within the
  timeout (5 minutes by default).
- After the timeout, the next message starts a new session. The assistant remembers nothing of
  the previous one, except what is in its long-term memory.
- A session keeps the model, effort, web search and memory settings it started with. Changes
  to these settings apply to new sessions.
- If the app restarts during a session, the session continues where it was.
- Sessions with no messages for longer than **Days to keep sessions** (30 by default) are
  deleted, together with their messages. Long-term memory is not affected.

## Attachments

- A message can carry files: images, PDFs and text files. The assistant opens them with
  **Read files**, so it must be on when the session starts.
- To attach files, paste them, drop them anywhere on the chat or select the paperclip.
- Files stay in your browser until you send the message. Then they are kept with the session
  and deleted together with it.
- Select a picture to open it, and download it from there. Select another file to download it.
- Each file can be at most 16 MB, the most Home Assistant lets through.

## Voice

You can talk to the assistant through Home Assistant Assist, from a voice assistant device or
the Assist dialog. This needs a second part, the HA Claude Code Assist integration, which
passes what you say to the app and its answer back.

1. Install the integration from the Marketplace (**Settings** > **Marketplace**). This button
   opens it there. Select **Install**, then **Restart Home Assistant**. The first time, the
   Marketplace asks you to connect GitHub.

   [![Open the HA Claude Code Assist integration in your Home Assistant Marketplace.](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=giuvincenzi&repository=ha-claude-code-assist&category=integration)

   Home Assistant 2026.10 has no Marketplace yet, so there you install it with
   [HACS](https://hacs.xyz). Add this repository as a
   [custom repository](https://hacs.xyz/docs/faq/custom_repositories/) of the **Integration**
   type, download **HA Claude Code Assist**, then restart Home Assistant.
2. With the app running, go to **Settings** > **Devices & services**. HA Claude Code Assist is
   under **Discovered**. Select **Add** and confirm.
3. Go to **Settings** > **Voice assistants**, open an assistant or select **Add assistant**, and
   choose HA Claude Code Assist as **Conversation agent**.
4. Turn on **Prefer handling commands locally** if you want Home Assistant to handle simple
   commands, such as turning on a light, by itself. They are faster that way, and everything
   else still goes to the assistant.

- Each voice assistant device has its own session, which ends after the same timeout as the
  chat. When you type in the Assist dialog, the session is your own, separate from the chat.
  Voice sessions are listed in **Sessions** with the others.
- The assistant uses the same settings, tools and memory as in the chat.
- The answer reaches Assist while it is written, so speech can start before it is complete
  when your text-to-speech supports it.
- If the app is stopped, Assist says that HA Claude Code Assist does not answer.

## Tools

The assistant can only do what its tools allow. Without tools it can still answer general
questions, tell the time and use its memory, but it cannot see or control your home.

Tools come from MCP servers (Model Context Protocol). Add them in **Tools** > **MCP servers**.
Select **Add MCP server**, give the server a name and write its configuration in Claude Code's
format:

```json
{
  "type": "http",
  "url": "<address>",
  "headers": {
    "<header>": "<value>"
  }
}
```

Then select **Save**. Every server is checked, and its card shows whether it connected and how
many tools it has, or what went wrong. Every tool of every server is available to the
assistant. The servers must be reachable from the app over HTTP. The name `ha_cca` is reserved
for the app.

### Home Assistant's MCP Server (recommended)

Home Assistant's own [Model Context Protocol Server](https://www.home-assistant.io/integrations/mcp_server/)
integration lets the assistant read and control the entities you expose to voice assistants,
and it is light on your subscription.

Once the integration is set up, add an MCP server named `home-assistant` with this
configuration:

```json
{
  "type": "http",
  "url": "http://homeassistant:8123/api/mcp",
  "headers": {
    "Authorization": "Bearer <long-lived access token>"
  }
}
```

- Replace `<long-lived access token>` with a token created in your Home Assistant user profile,
  in the **Security** tab under **Long-lived access tokens**.
- Replace `8123` with the port you open Home Assistant with, if it is different.

### Other MCP servers

Any MCP server reachable over HTTP works, for example
[ha-mcp](https://github.com/homeassistant-ai/ha-mcp), a third-party server for history,
automations, configuration and more, or one of your own. For ha-mcp, add a server named
`ha-mcp`:

```json
{
  "type": "http",
  "url": "http://<home-assistant-address>:9584/private_<key>"
}
```

### Web search

**Web search**, in **Tools** > **Built-in tools**, lets the assistant search the web and read
web pages, for news, weather and other up-to-date information. It is off by default.

### Read files

**Read files**, in **Tools** > **Built-in tools**, lets the assistant open images, PDFs and text
files, such as a picture it downloads from the web. It can read only the files of its own
session, never those of another session or of the app. It is on by default.

### Tools and your subscription

The description of every tool is sent to the model with every request. Many or large tools use
more of your subscription and make the first answer after a pause slower. A server with many
tools can add around 100,000 tokens to each request, while Home Assistant's MCP Server adds
around 10,000 with a few exposed entities. Keep only the tools you need.

## Long-term memory

- The assistant saves something only when you explicitly ask it to remember it, and removes
  it when you ask it to forget it.
- It never saves the state of your devices, because Home Assistant always has the current one.
- The **Memory** tab lists every entry, and you can add, edit and remove them there.
- When the memory is full, the assistant tells you, and nothing more is saved until you remove
  an entry.

## Settings

| Where | Setting | What it does |
|---|---|---|
| Settings > Claude Code | Setup token | The Claude subscription the assistant uses (see [Getting started](#getting-started)). When it expires or is revoked, the chat says that the token was rejected and the panel shows "Setup token rejected". Create a new one and paste it here. |
| Settings > Claude Code | Model | Haiku is the fastest and uses the least of your subscription. Sonnet balances speed and capability. Opus is the most capable, but it is slower and uses the most. |
| Settings > Claude Code | Effort | How much the assistant thinks before answering. Higher effort gives more careful answers, but they are slower and use more of your subscription. |
| Settings > Sessions | Timeout in minutes | A session ends after this many minutes without messages. |
| Settings > Sessions | Days to keep sessions | Sessions with no messages for longer than this are deleted, together with their messages. |
| Settings > Memory | Long-term memory | Lets the assistant remember facts across sessions. |
| Settings > Memory | Maximum entries | The most facts long-term memory can hold. |
| Settings > Memory | Maximum entry length | The longest a single entry can be, in characters. |
| Tools > Built-in tools | Web search | Lets the assistant search the web and read web pages. |
| Tools > Built-in tools | Read files | Lets the assistant open images, PDFs and text files of its own session. |
| Tools | MCP servers | The assistant's tools (see [Tools](#tools)). |

Settings changed in the panel apply right away to new sessions. The same settings are in the
app's **Configuration** tab in Home Assistant, where changes apply after the app restarts.
