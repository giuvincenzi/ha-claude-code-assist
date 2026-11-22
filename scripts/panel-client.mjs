// Client of the app panel for the tests: logs in to the test Home Assistant as the test user,
// opens an Ingress session and talks to the panel exactly as the browser does.

export const HA_URL = process.env.HA_URL ?? "http://dev:80";
export const APP = process.env.APP ?? "local_ha_claude_code_assist";
const CLIENT_ID = `${HA_URL}/`;

async function json(response) {
  if (!response.ok) throw new Error(`${response.url}: HTTP ${response.status}`);
  return response.json();
}

export async function login() {
  const { TEST_HA_USERNAME: username, TEST_HA_PASSWORD: password } = process.env;
  const flow = await json(await fetch(`${HA_URL}/auth/login_flow`, {
    method: "POST",
    body: JSON.stringify({ client_id: CLIENT_ID, handler: ["homeassistant", null], redirect_uri: CLIENT_ID }),
  }));
  const step = await json(await fetch(`${HA_URL}/auth/login_flow/${flow.flow_id}`, {
    method: "POST",
    body: JSON.stringify({ client_id: CLIENT_ID, username, password }),
  }));
  const token = await json(await fetch(`${HA_URL}/auth/token`, {
    method: "POST",
    body: new URLSearchParams({ grant_type: "authorization_code", code: step.result, client_id: CLIENT_ID }),
  }));
  return token.access_token;
}

/** Sends commands to Home Assistant's WebSocket API, in order, and returns their results. */
export async function homeAssistantCalls(accessToken, calls) {
  const ws = new WebSocket(`${HA_URL.replace(/^http/, "ws")}/api/websocket`);
  const results = [];
  await new Promise((resolve, reject) => {
    let id = 0;
    ws.onerror = () => reject(new Error("Home Assistant WebSocket error"));
    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === "auth_required") ws.send(JSON.stringify({ type: "auth", access_token: accessToken }));
      else if (message.type === "auth_invalid") reject(new Error("Home Assistant auth failed"));
      else if (message.type === "result" && !message.success) reject(new Error(JSON.stringify(message.error)));
      else if (message.type === "result") results.push(message.result);
      if (message.type === "auth_ok" || message.type === "result") {
        if (id < calls.length) ws.send(JSON.stringify({ id: ++id, ...calls[id - 1] }));
        else { ws.close(); resolve(); }
      }
    };
  });
  return results;
}

/** Sends Supervisor API calls through Home Assistant's WebSocket API, in order. */
export function supervisorCalls(accessToken, calls) {
  return homeAssistantCalls(accessToken, calls.map((call) => ({ type: "supervisor/api", ...call })));
}

/**
 * Sends a sentence to the preferred voice assistant, as the Assist dialog does: it goes to the
 * assistant's conversation agent. Returns the events of the run and its result.
 */
export async function assist(accessToken, text, conversationId = null) {
  const ws = new WebSocket(`${HA_URL.replace(/^http/, "ws")}/api/websocket`);
  const events = [];
  await new Promise((resolve, reject) => {
    ws.onerror = () => reject(new Error("Home Assistant WebSocket error"));
    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === "auth_required") ws.send(JSON.stringify({ type: "auth", access_token: accessToken }));
      else if (message.type === "auth_invalid") reject(new Error("Home Assistant auth failed"));
      else if (message.type === "auth_ok") {
        ws.send(JSON.stringify({ id: 1, type: "assist_pipeline/run", start_stage: "intent", end_stage: "intent",
          input: { text }, conversation_id: conversationId }));
      } else if (message.type === "result" && !message.success) reject(new Error(JSON.stringify(message.error)));
      else if (message.type === "event") {
        events.push(message.event);
        if (message.event.type === "error") reject(new Error(JSON.stringify(message.event.data)));
        if (message.event.type === "run-end") { ws.close(); resolve(); }
      }
    };
  });
  const result = events.find((e) => e.type === "intent-end").data.intent_output;
  return { events, result, speech: result.response.speech.plain.speech };
}

/**
 * The MCP servers the tests use: only the test Home Assistant's own MCP Server, with the test
 * user's access token (valid 30 minutes, longer than a run). The servers configured in the panel
 * are never used by a test: they can point to a real home.
 */
export function testMcpServers(accessToken) {
  return JSON.stringify({ mcpServers: { "home-assistant": {
    type: "http", url: "http://homeassistant:80/api/mcp", headers: { Authorization: `Bearer ${accessToken}` },
  } } });
}

/** Ingress address and cookie of the app panel. */
export async function ingress(accessToken) {
  const [session, info] = await supervisorCalls(accessToken, [
    { endpoint: "/ingress/session", method: "post" },
    { endpoint: `/addons/${APP}/info`, method: "get" },
  ]);
  return { info, base: `${HA_URL}${info.ingress_url}`, headers: { Cookie: `ingress_session=${session.session}` } };
}

/** The panel's WebSocket protocol: commands with a result, and pushed events. */
export class Panel {
  constructor(base, headers) {
    this.ws = new WebSocket(`${base.replace(/^http/, "ws")}ws`, { headers });
    this.nextId = 1;
    this.pending = new Map();
    this.events = [];
    this.waiters = [];
    this.ws.onmessage = (message) => {
      const data = JSON.parse(message.data);
      if (data.type === "result") {
        const { resolve, reject } = this.pending.get(data.id);
        this.pending.delete(data.id);
        data.success ? resolve(data.result) : reject(new Error(data.error));
      } else if (data.type === "event") {
        this.events.push(data.event);
        this.waiters = this.waiters.filter((w) => !(w.match(data.event) && (w.resolve(data.event), true)));
      }
    };
  }

  open() {
    return new Promise((resolve, reject) => {
      this.ws.onopen = resolve;
      this.ws.onerror = () => reject(new Error("panel WebSocket error"));
    });
  }

  close() {
    this.ws.close();
  }

  request(type, payload = {}) {
    const id = this.nextId++;
    this.ws.send(JSON.stringify({ id, type, ...payload }));
    return new Promise((resolve, reject) => this.pending.set(id, { resolve, reject }));
  }

  waitFor(match, timeoutMs = 180000) {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error("timed out waiting for an event")), timeoutMs);
      this.waiters.push({ match, resolve: (e) => { clearTimeout(timer); resolve(e); } });
    });
  }

  /** Sends one message and returns the turn: answer, tool calls, Claude Code's result event. */
  async chat(conversationId, text, attachments = []) {
    const start = this.events.length;
    const { session_id: sessionId } = await this.request("chat/send", { conversation_id: conversationId, text, attachments });
    const finished = this.events.slice(start).find((e) => e.type === "turn_finished" && e.session_id === sessionId)
      ?? await this.waitFor((e) => e.type === "turn_finished" && e.session_id === sessionId);
    const turn = this.events.slice(start).filter((e) => e.type === "turn_event" && e.session_id === sessionId)
      .map((e) => e.event);
    const tools = [];
    for (const event of turn) {
      for (const block of Array.isArray(event.message?.content) ? event.message.content : []) {
        if (event.type === "assistant" && block.type === "tool_use") tools.push({ name: block.name, input: block.input });
        if (event.type === "user" && block.type === "tool_result" && block.is_error) {
          tools.push({ error: typeof block.content === "string" ? block.content : JSON.stringify(block.content) });
        }
      }
    }
    return { sessionId, finished, tools, result: turn.find((e) => e.type === "result"), events: turn };
  }
}
