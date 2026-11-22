import { formatCompact } from "./format";
import type { ClaudeSession, TokenStatus } from "./types";

/** Every token the conversation's model calls processed (input, output, cache read and written);
 * null until the first answer. */
export function totalTokens(claude: ClaudeSession): number | null {
  if (claude.input_tokens === null) return null;
  return (claude.input_tokens ?? 0) + (claude.output_tokens ?? 0)
    + (claude.cache_read_input_tokens ?? 0) + (claude.cache_creation_input_tokens ?? 0);
}

/** How much of the context window is used, as a whole percentage ("less than 1" counts as 1);
 * null while unknown. */
export function contextPercent(claude: ClaudeSession): number | null {
  const { context_tokens: tokens, context_window: window } = claude;
  if (tokens === null || !window) return null;
  return tokens > 0 ? Math.max(1, Math.round((tokens / window) * 100)) : 0;
}

/** How full the context is: "122K of 1M tokens (12%)", or "110K tokens" while the window is not
 * known yet. */
export function contextLabel(claude: ClaudeSession): string | null {
  const { context_tokens: tokens, context_window: window } = claude;
  if (tokens === null) return null;
  if (!window) return `${formatCompact(tokens)} tokens`;
  return `${formatCompact(tokens)} of ${formatCompact(window)} tokens (${contextPercent(claude)}%)`;
}

const DAY = 24 * 60 * 60 * 1000;
/** From when the setup token's expiry is worth a warning. */
const EXPIRY_WARNING_DAYS = 30;

export interface TokenProblem {
  label: string;
  hint: string;
  tone: "warn" | "error";
}

/** What is wrong with the setup token, if anything: missing, rejected, expired or expiring soon
 * (the expiry is an estimate: one year from when the token was first seen). */
export function tokenProblem(token: TokenStatus, now = Date.now()): TokenProblem | null {
  const renew = "Create a new one with claude setup-token and paste it in Settings.";
  if (!token.configured) return { label: "missing", hint: "Paste your setup token in Settings.", tone: "error" };
  if (token.rejected_at) return { label: "rejected", hint: `Claude did not accept it. ${renew}`, tone: "error" };
  if (!token.expires_at) return null;
  const days = Math.ceil((new Date(token.expires_at).getTime() - now) / DAY);
  if (days <= 0) return { label: "expired", hint: renew, tone: "error" };
  if (days <= EXPIRY_WARNING_DAYS) {
    return { label: `expires in ${days} day${days === 1 ? "" : "s"}`, hint: renew, tone: "warn" };
  }
  return null;
}
