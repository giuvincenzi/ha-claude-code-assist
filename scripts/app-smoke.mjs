// End-to-end smoke test through Home Assistant's Ingress proxy, as the browser does: panel page
// and API, WebSocket, settings saved through the Supervisor, a real chat with Claude, memory,
// resume after an app restart, transcripts; and Assist, through Home Assistant's conversation
// API and the integration. Fails on the first check that does not hold.

import { deflateSync } from "node:zlib";

import {
  APP, Panel, assist, homeAssistantCalls, ingress, login, supervisorCalls, testMcpServers,
} from "./panel-client.mjs";

/** A 64x64 red PNG, made here so the test needs no file. */
function redSquarePng() {
  const size = 64;
  const row = Buffer.concat([Buffer.from([0]), Buffer.alloc(size * 3, Buffer.from([220, 20, 20]))]);
  const crc = (buffer) => {
    let c = ~0;
    for (const byte of buffer) {
      c ^= byte;
      for (let k = 0; k < 8; k++) c = (c >>> 1) ^ (0xedb88320 & -(c & 1));
    }
    return ~c >>> 0;
  };
  const chunk = (type, data) => {
    const body = Buffer.concat([Buffer.from(type), data]);
    const out = Buffer.alloc(body.length + 8);
    out.writeUInt32BE(data.length, 0);
    body.copy(out, 4);
    out.writeUInt32BE(crc(body), body.length + 4);
    return out;
  };
  const header = Buffer.alloc(13);
  header.writeUInt32BE(size, 0);
  header.writeUInt32BE(size, 4);
  header.set([8, 2, 0, 0, 0], 8);
  return Buffer.concat([Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]), chunk("IHDR", header),
    chunk("IDAT", deflateSync(Buffer.concat(Array(size).fill(row)))), chunk("IEND", Buffer.alloc(0))]);
}

/** Every Read call of a turn: the path, and whether Claude Code refused it. */
function reads(turn) {
  const calls = new Map();
  for (const event of turn.events) {
    for (const block of Array.isArray(event.message?.content) ? event.message.content : []) {
      if (event.type === "assistant" && block.type === "tool_use" && block.name === "Read") {
        calls.set(block.id, { path: block.input.file_path, refused: undefined });
      }
      if (event.type === "user" && block.type === "tool_result" && calls.has(block.tool_use_id)) {
        calls.get(block.tool_use_id).refused = Boolean(block.is_error);
      }
    }
  }
  return [...calls.values()];
}

function check(condition, message) {
  if (!condition) throw new Error(message);
  console.log(`ok  ${message}`);
}

const accessToken = await login();
check(Boolean(accessToken), "logged in as the test user");

const { info, base, headers } = await ingress(accessToken);
check(info.state === "started", `app state is ${info.state}`);

const page = await fetch(base, { headers });
check(page.ok && (await page.text()).includes("hca-app"), "panel page served through Ingress");

const status = await (await fetch(`${base}api/status`, { headers })).json();
check(Boolean(status.claude_code_version), `Claude Code in the app: ${status.claude_code_version}`);
check(status.token.configured, "OAuth token configured");

let panel = new Panel(base, headers);
await panel.open();
check(true, "panel WebSocket through Ingress");

const settings = await panel.request("settings/get");
// The tests use only the test Home Assistant's MCP Server: the servers configured in the panel can
// point to a real home. The configured ones are put back at the end, also when a check fails.
await panel.request("settings/update", { changes: { mcp_servers: testMcpServers(accessToken), read_files: true } });
try {
  check(settings.token.configured && settings.values.model, `settings: model ${settings.values.model}, effort ${settings.values.effort}`);

  // Another open panel (another tab or device) hears of the change, so its status bar refreshes.
  const other = new Panel(base, headers);
  await other.open();
  const announced = other.waitFor((e) => e.type === "settings_changed", 30000);
  // Saving goes through the Supervisor API (/addons/self/options).
  const changed = await panel.request("settings/update", { changes: { session_timeout_minutes: 7 } });
  const [stored] = await supervisorCalls(accessToken, [{ endpoint: `/addons/${APP}/info`, method: "get" }]);
  check(changed.values.session_timeout_minutes === 7 && stored.options.session_timeout_minutes === 7,
    "settings saved through the Supervisor");
  await announced;
  other.close();
  check(true, "the change announced to every open panel");
  await panel.request("settings/update", { changes: { session_timeout_minutes: settings.values.session_timeout_minutes } });
  await panel.request("settings/update", { changes: { mcp_servers: '{"mcpServers": {"ha_cca": {}}}' } })
    .then(() => check(false, "reserved MCP name rejected"), (err) => check(/reserved/.test(err.message), "reserved MCP name rejected"));

  // Messages of the same user go to its active session: the test starts from none, as after
  // "New session", so it never mixes with a conversation left open in the panel.
  for (const open of await panel.request("sessions/list")) {
    if (open.active && !open.busy) await panel.request("sessions/close", { session_id: open.session_id });
  }

  const conversation = `smoke-${Date.now()}`;
  const first = await panel.chat(conversation, "Reply with exactly this word and nothing else: pong");
  check(!first.finished.is_error && /pong/i.test(first.finished.text), `chat answered: ${JSON.stringify(first.finished.text)}`);
  check(first.events.some((e) => e.type === "stream_event"), "answer streamed");

  const second = await panel.chat(conversation,
    "Please remember this: the smoke test colour is ultramarine. Confirm in one short sentence.");
  check(second.sessionId === first.sessionId, "same conversation, same session");

  // App restart: the Claude Code process is gone; the next message must resume the session.
  panel.close();
  await supervisorCalls(accessToken, [{ endpoint: `/addons/${APP}/restart`, method: "post" }]);
  for (let attempt = 0; ; attempt++) {
    const response = await fetch(base, { headers }).catch(() => null);
    if (response?.ok) break;
    if (attempt > 60) throw new Error("app did not come back after restart");
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  panel = new Panel(base, headers);
  await panel.open();
  const third = await panel.chat(conversation, "Which word did I ask you to reply with at the very beginning? Answer with the word only.");
  check(third.sessionId === first.sessionId && /pong/i.test(third.finished.text),
    `after an app restart the session was resumed: ${JSON.stringify(third.finished.text)}`);

  const memory = await panel.request("memory/list");
  const saved = memory.entries.find((e) => /ultramarine/i.test(e.text));
  check(saved && saved.created_by === "claude" && saved.conversation_id === first.sessionId,
    `Claude saved memory entry #${saved?.id} with its conversation`);
  await panel.request("memory/remove", { entry_id: saved.id });
  check(!(await panel.request("memory/list")).entries.some((e) => e.id === saved.id), "memory entry removed from the panel");

  const sessions = await panel.request("sessions/list");
  const session = sessions.find((s) => s.session_id === first.sessionId);
  check(session?.active && session.settings.model === settings.values.model && session.claude.context_tokens > 0
    && session.claude.context_window > 0 && session.claude.input_tokens > 0,
    `session listed: ${session?.settings.model}, context ${session?.claude.context_tokens} of ${session?.claude.context_window} tokens`);
  const history = await panel.request("sessions/history", { session_id: first.sessionId });
  check(history.filter((i) => i.kind === "user").length === 3 && history.some((i) => i.kind === "tool"),
    `transcript readable: ${history.length} items`);

  await panel.request("sessions/close", { session_id: first.sessionId });
  const closed = (await panel.request("sessions/list")).find((s) => s.session_id === first.sessionId);
  check(!closed.active && closed.closed_at, "session closed from the panel");

  // Read reaches only the session's own files: from a second session, Claude Code refuses the
  // first one's transcript and record, the app's options, and the session's own record.
  const firstIds = (await panel.request("sessions/list")).find((s) => s.session_id === first.sessionId);
  const foreign = [
    `/data/claude/projects/-data-sessions-${first.sessionId}-workdir/${firstIds.claude.session_id}.jsonl`,
    `/data/sessions/${first.sessionId}/session.json`,
    "/data/options.json",
  ];
  const probeChat = `smoke-read-${Date.now()}`;
  const probe = await panel.chat(probeChat,
    `Use the Read tool on each of these files, one by one, and say only whether each worked: ${foreign.join(", ")}`);
  const tried = reads(probe);
  check(foreign.every((path) => tried.some((r) => r.path === path && r.refused)),
    `Read refused another session's files and the app's options: ${JSON.stringify(tried)}`);
  const ownRecord = `/data/sessions/${probe.sessionId}/session.json`;
  const own = await panel.chat(probeChat, `Use the Read tool on ${ownRecord} and say only whether it worked.`);
  check(reads(own).some((r) => r.path === ownRecord && r.refused), "Read refused the session's own record");
  await panel.request("sessions/close", { session_id: probe.sessionId });

  // An image from the web: WebFetch saves it among the session's own files and Claude opens it
  // with Read. A new session, so it starts with web search on.
  await panel.request("settings/update", { changes: { web_search: true, read_files: true } });
  const image = await panel.chat(`smoke-image-${Date.now()}`, "What is in this picture? https://www.gstatic.com/webp/gallery/1.jpg");
  const opened = reads(image).find((r) => r.path.includes(`/-data-sessions-${image.sessionId}-workdir/`));
  check(opened && !opened.refused && /fjord/i.test(image.finished.text),
    `an image from the web opened by Claude: ${JSON.stringify(image.finished.text.slice(0, 120))}`);
  await panel.request("sessions/close", { session_id: image.sessionId });

  // A file attached in the panel: uploaded into the session over HTTP, opened by Claude with Read,
  // shown in the history as a file (not as the line that tells Claude where it is).
  const attachChat = `smoke-attach-${Date.now()}`;
  const prepared = await panel.request("chat/prepare", { conversation_id: attachChat });
  const upload = await fetch(`${base}api/sessions/${prepared.session_id}/attachments?name=square.png`, {
    method: "POST", headers: { ...headers, "Content-Type": "application/octet-stream" }, body: redSquarePng(),
  });
  const { name: savedName } = await upload.json();
  check(upload.ok && savedName === "square.png", "a file uploaded into the session");
  const attached = await panel.chat(attachChat, "What colour is this square? Answer with one word.", [savedName]);
  const openedFile = reads(attached).find((r) => r.path.endsWith(`/sessions/${prepared.session_id}/workdir/attachments/square.png`));
  check(attached.sessionId === prepared.session_id && openedFile && !openedFile.refused && /red/i.test(attached.finished.text),
    `the attached file opened by Claude: ${JSON.stringify(attached.finished.text.slice(0, 80))}`);
  const attachedHistory = await panel.request("sessions/history", { session_id: attached.sessionId });
  const sentItem = attachedHistory.find((i) => i.kind === "user");
  check(sentItem.text === "What colour is this square? Answer with one word."
    && JSON.stringify(sentItem.attachments) === JSON.stringify([{ name: "square.png", image: true }]),
    "the history shows the attached file, not its line");
  const picture = await fetch(`${base}api/sessions/${attached.sessionId}/attachments/square.png`, { headers });
  check(picture.ok && picture.headers.get("content-type") === "image/png" && picture.headers.get("x-content-type-options") === "nosniff",
    "the attached picture served to the panel");
  const downloaded = await fetch(`${base}api/sessions/${attached.sessionId}/attachments/square.png/download`, { headers });
  check(downloaded.ok && downloaded.headers.get("content-disposition")?.startsWith("attachment;")
    && Buffer.from(await downloaded.arrayBuffer()).equals(redSquarePng()), "the attached file downloaded as it was sent");
  const tooLarge = await fetch(`${base}api/sessions/${attached.sessionId}/attachments?name=big.bin`, {
    method: "POST", headers: { ...headers, "Content-Type": "application/octet-stream" }, body: new Uint8Array(17 * 1024 * 1024),
  });
  check(tooLarge.status === 413, `a file over 16 MB refused by Home Assistant: HTTP ${tooLarge.status}`);
  await panel.request("sessions/close", { session_id: attached.sessionId });

  // Deleting removes the conversation from the list and its transcript (its history is gone).
  await panel.request("sessions/delete", { session_id: first.sessionId });
  const deleted = !(await panel.request("sessions/list")).some((s) => s.session_id === first.sessionId);
  const historyGone = await panel.request("sessions/history", { session_id: first.sessionId }).then(() => false, () => true);
  check(deleted && historyGone, "session deleted from the panel");

  // Assist: the voice assistant sends the sentence to its agent, the integration, which sends it
  // to the app; the app answers from a voice session of the user who spoke (no voice device here).
  const [entries, registry, pipelines] = await homeAssistantCalls(accessToken, [
    { type: "config_entries/get", domain: "ha_claude_code_assist" },
    { type: "config/entity_registry/list" },
    { type: "assist_pipeline/pipeline/list" },
  ]);
  check(entries.length === 1 && entries[0].state === "loaded" && entries[0].source === "hassio",
    "the integration set up from the app's discovery");
  const agentId = registry.find((e) => e.config_entry_id === entries[0].entry_id && e.entity_id.startsWith("conversation."))?.entity_id;
  const assistant = pipelines.pipelines.find((p) => p.id === pipelines.preferred_pipeline);
  check(assistant.conversation_engine === agentId, `the voice assistant ${JSON.stringify(assistant.name)} uses ${agentId}`);
  const spoken = await assist(accessToken, "Reply with exactly this word and nothing else: pong");
  const streamed = spoken.events.filter((e) => e.type === "intent-progress" && e.data.chat_log_delta?.content);
  check(spoken.result.response.response_type === "action_done" && /pong/i.test(spoken.speech) && streamed.length > 0,
    `Assist answered: ${JSON.stringify(spoken.speech)}, streamed in ${streamed.length} parts`);
  const again = await assist(accessToken, "Which word did you just reply with? Answer with the word only.",
    spoken.result.conversation_id);
  // The sessions holding this conversation: exactly one, a voice session of the user who spoke. Other voice sessions
  // may be listed (Assist used by hand in the test environment), so the check looks for this one only.
  const voice = (await panel.request("sessions/list"))
    .filter((s) => s.conversation_ids.includes(spoken.result.conversation_id));
  check(voice.length === 1 && voice[0].source.channel === "voice" && voice[0].source.key.startsWith("user:")
    && again.result.conversation_id === spoken.result.conversation_id && /pong/i.test(again.speech),
    `one voice session for the conversation, named ${JSON.stringify(voice[0]?.source.name)}`);
  await panel.request("sessions/close", { session_id: voice[0].session_id });
  await panel.request("sessions/delete", { session_id: voice[0].session_id });

  // A rejected token is reported as an error with what to do, then cleared by the right token.
  await panel.request("settings/update", { changes: { claude_code_oauth_token: "sk-ant-oat01-rejected-by-the-smoke-test" } });
  const rejected = await panel.chat(`smoke-token-${Date.now()}`, "Reply with ok");
  const rejectedStatus = await panel.request("status/get");
  check(rejected.finished.is_error && rejected.finished.error === "authentication_failed"
    && /token was rejected/.test(rejected.finished.text) && rejectedStatus.token_rejected_at,
    "rejected token reported clearly");
  await panel.request("sessions/close", { session_id: rejected.sessionId });
  await panel.request("settings/update", { changes: { claude_code_oauth_token: process.env.CLAUDE_CODE_OAUTH_TOKEN } });
  const restored = await panel.chat(`smoke-token-${Date.now()}`, "Reply with exactly this word and nothing else: pong");
  check(!restored.finished.is_error && !(await panel.request("status/get")).token_rejected_at,
    "the right token clears the error");
  await panel.request("sessions/close", { session_id: restored.sessionId });
} finally {
  panel.close();
  const restore = new Panel(base, headers);
  await restore.open();
  const { mcp_servers, web_search, read_files } = settings.values;
  await restore.request("settings/update", { changes: { mcp_servers, web_search, read_files } });
  restore.close();
}
