/** The settings a conversation runs with (never secrets). */
export interface SessionSettings {
  model: string;
  effort: string;
  web_search: boolean;
  memory_enabled: boolean;
  read_files: boolean;
  /** Names of the MCP servers at the conversation process's last start. */
  mcp_servers: string[];
}

/** What Claude Code reports about a conversation: only what the panel shows. */
export interface ClaudeSession {
  /** The id Claude Code reported for the conversation; null until it answers. */
  session_id: string | null;
  /** Size of the context at the last model call, and the model's context window. */
  context_tokens: number | null;
  context_window: number | null;
  /** Totals of the whole conversation; null until the first answer. */
  input_tokens: number | null;
  output_tokens: number | null;
  cache_read_input_tokens: number | null;
  cache_creation_input_tokens: number | null;
  web_search_requests: number | null;
  /** Kept for reference, never shown: with a subscription nothing is billed per call. */
  cost_usd: number | null;
}

export interface Session {
  /** Ours: the record's key, created before Claude Code starts. Not Claude Code's own id. */
  session_id: string;
  title: string;
  source: { channel: string; key: string; name?: string };
  conversation_ids: string[];
  created_at: string;
  last_activity: string;
  closed_at: string | null;
  settings: SessionSettings;
  claude: ClaudeSession;
  active: boolean;
  busy: boolean;
  process_running: boolean;
}

export interface MemoryEntry {
  id: number;
  text: string;
  created_at: string;
  created_by: "claude" | "user";
  conversation_id: string | null;
}

export interface TokenStatus {
  configured: boolean;
  configured_at?: string;
  expires_at?: string;
  /** When Claude Code last rejected it; cleared by the next answered turn or a new token. */
  rejected_at?: string | null;
}

export interface SettingsView {
  values: {
    model: string;
    effort: string;
    web_search: boolean;
    read_files: boolean;
    mcp_servers: string;
    session_timeout_minutes: number;
    session_retention_days: number;
    memory_enabled: boolean;
    memory_max_entries: number;
    memory_max_entry_length: number;
  };
  token: TokenStatus;
  choices: { model: string[]; effort: string[] };
}

export interface Status {
  claude_code_version: string | null;
  token: TokenStatus;
  token_rejected_at: string | null;
  mcp_servers: string[];
  /** Sessions with a message within the timeout, of any user or channel. */
  active_sessions: number;
}

/** A conversation item, from a transcript or built live from turn events. */
/** A file attached to a user's message. */
export interface ChatAttachment {
  name: string;
  /** A picture the panel can show; other files are shown by name. */
  image: boolean;
  /** Where the picture is while the message is sent (a preview in the browser). */
  url?: string;
  loading?: boolean;
  failed?: boolean;
}

export type ChatItem = (
  | { kind: "user"; text: string; attachments?: ChatAttachment[] }
  | { kind: "assistant"; text: string; duration_ms?: number }
  | { kind: "tool"; id?: string; name: string; input: unknown; result: string | null; is_error: boolean }
  | { kind: "error"; text: string }
) & { timestamp?: string | null };

// Events pushed by the core.
export type CoreEvent =
  | { type: "session_updated"; session: Session }
  | { type: "session_deleted"; session_id: string }
  | { type: "turn_started"; session_id: string; text: string }
  | { type: "turn_event"; session_id: string; event: ClaudeEvent }
  | { type: "turn_finished"; session_id: string; is_error: boolean; error: string | null; text: string }
  | { type: "memory_changed" }
  /** The settings changed, from this panel or another one: anything that shows them reloads. */
  | { type: "settings_changed" };

// Subset of Claude Code stream-json events used by the panel.
export interface ClaudeEvent {
  type: string;
  duration_ms?: number;
  event?: {
    type: string;
    content_block?: { type: string };
    delta?: { type: string; text?: string };
  };
  message?: { content?: unknown };
}
