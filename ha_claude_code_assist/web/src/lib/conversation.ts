import type { ChatItem, ClaudeEvent } from "./types";

const CONVERSATION_KEY = "hca.conversation_id";

/** UUID v4. crypto.randomUUID() exists only in secure contexts, and Home Assistant is often
 * opened over plain HTTP on the local network. */
function uuid4(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

/** A new conversation id, remembered by this browser so a reload shows the same chat. */
export function newConversationId(): string {
  const id = uuid4();
  try {
    localStorage.setItem(CONVERSATION_KEY, id);
  } catch {
    /* storage unavailable: a new conversation per load */
  }
  return id;
}

/** The conversation id this browser was using, or a new one. */
export function currentConversationId(): string {
  try {
    const existing = localStorage.getItem(CONVERSATION_KEY);
    if (existing) return existing;
  } catch {
    /* storage unavailable */
  }
  return newConversationId();
}

interface Block {
  type: string;
  id?: string;
  name: string;
  input?: unknown;
  tool_use_id?: string;
  content?: unknown;
  is_error?: boolean;
}

function contentBlocks(event: ClaudeEvent): Block[] {
  const content = event.message?.content;
  return Array.isArray(content) ? (content as Block[]) : [];
}

function resultText(content: unknown): string {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) return content.map((c) => (c as { text?: string }).text ?? "").join("\n");
  return JSON.stringify(content);
}

/** The conversation items after one Claude Code event: streamed text, tool calls and their results. */
export function applyClaudeEvent(current: ChatItem[], event: ClaudeEvent): ChatItem[] {
  const items = [...current];
  const now = new Date().toISOString();
  if (event.type === "stream_event" && event.event) {
    const inner = event.event;
    if (inner.type === "content_block_start" && inner.content_block?.type === "text") {
      items.push({ kind: "assistant", text: "", timestamp: now });
    } else if (inner.type === "content_block_delta" && inner.delta?.type === "text_delta") {
      const last = items[items.length - 1];
      if (last?.kind === "assistant") items[items.length - 1] = { ...last, text: last.text + (inner.delta.text ?? "") };
      else items.push({ kind: "assistant", text: inner.delta.text ?? "", timestamp: now });
    }
  } else if (event.type === "assistant") {
    for (const block of contentBlocks(event)) {
      if (block.type === "tool_use") {
        items.push({ kind: "tool", id: block.id, name: block.name, input: block.input, result: null, is_error: false, timestamp: now });
      }
    }
  } else if (event.type === "user") {
    for (const block of contentBlocks(event)) {
      if (block.type !== "tool_result") continue;
      const index = items.findIndex((item) => item.kind === "tool" && item.id === block.tool_use_id);
      const tool = items[index];
      if (tool?.kind === "tool") items[index] = { ...tool, result: resultText(block.content), is_error: Boolean(block.is_error) };
    }
  } else if (event.type === "result" && event.duration_ms !== undefined) {
    // The response time of the whole turn, shown under its last answer.
    for (let i = items.length - 1; i >= 0; i--) {
      const item = items[i];
      if (item.kind === "user") break;
      if (item.kind === "assistant" && item.text) {
        items[i] = { ...item, duration_ms: event.duration_ms };
        break;
      }
    }
  }
  return items;
}
