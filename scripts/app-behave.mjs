// Behaviour report: talks to the assistant through the panel, one conversation per scenario of
// app-behave.json, and prints for every message the answer, the tools called, the model turns
// and the time. It checks nothing by itself: the report is read to judge the behaviour, for
// example before and after a change to the system prompt.
//
// A scenario sets the settings it needs: "mcp": "none" removes the MCP servers, "mcp": "test"
// uses the test Home Assistant's MCP Server. The MCP servers configured in the panel are never
// used (they can point to a real home). The settings and the memory are restored at the end.

import { readFileSync } from "node:fs";

import { Panel, ingress, login, testMcpServers } from "./panel-client.mjs";

const scenarios = JSON.parse(readFileSync(new URL("./app-behave.json", import.meta.url), "utf8"));
const accessToken = await login();
const { base, headers } = await ingress(accessToken);
const panel = new Panel(base, headers);
await panel.open();

const initial = (await panel.request("settings/get")).values;
const initialMemory = (await panel.request("memory/list")).entries;

function short(value, length = 100) {
  const text = typeof value === "string" ? value : JSON.stringify(value);
  return text.length > length ? `${text.slice(0, length)}…` : text;
}

async function closeActiveSessions() {
  for (const session of await panel.request("sessions/list")) {
    if (session.active && !session.busy) await panel.request("sessions/close", { session_id: session.session_id });
  }
}

async function setMemory(texts) {
  for (const entry of (await panel.request("memory/list")).entries) await panel.request("memory/remove", { entry_id: entry.id });
  for (const text of texts) await panel.request("memory/add", { text });
}

const totals = [];
try {
  for (const scenario of scenarios) {
    const { mcp, ...settings } = scenario.settings ?? {};
    const changes = { ...settings };
    if (mcp === "none") changes.mcp_servers = '{"mcpServers": {}}';
    if (mcp === "test") changes.mcp_servers = testMcpServers(accessToken);
    else if (mcp !== "none") throw new Error(`scenario "${scenario.name}": "mcp" must be "none" or "test"`);
    await panel.request("settings/update", { changes: { ...initial, ...changes } });
    await closeActiveSessions();
    if (scenario.memory) await setMemory(scenario.memory);

    console.log(`\n========== ${scenario.name} ==========`);
    const conversation = `behave-${Date.now()}`;
    for (const message of scenario.messages) {
      const turn = await panel.chat(conversation, message);
      const seconds = (turn.result?.duration_ms ?? 0) / 1000;
      const context = (await panel.request("sessions/list")).find((s) => s.session_id === turn.sessionId)?.claude.context_tokens;
      totals.push(seconds);
      console.log(`\n> ${message}\n< ${turn.finished.text.replace(/\n/g, "\n  ")}`);
      for (const tool of turn.tools) {
        console.log(tool.error ? `   ↳ error: ${short(tool.error, 160)}` : `   · ${tool.name.replace(/^mcp__/, "")} ${short(tool.input)}`);
      }
      console.log(`   [${turn.result?.num_turns ?? "?"} turns, ${seconds.toFixed(1)} s, context ${context ?? "?"}]`);
    }
  }
} finally {
  await closeActiveSessions();
  await panel.request("settings/update", { changes: initial });
  await setMemory(initialMemory.map((entry) => entry.text));
  panel.close();
}

const sorted = [...totals].sort((a, b) => a - b);
console.log(`\n${totals.length} messages, median ${sorted[Math.floor(sorted.length / 2)]?.toFixed(1)} s, max ${sorted.at(-1)?.toFixed(1)} s`);
