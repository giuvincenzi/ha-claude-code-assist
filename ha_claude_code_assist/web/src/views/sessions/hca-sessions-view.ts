import { LitElement, css, html, nothing } from "lit";
import { customElement, property, query, state } from "lit/decorators.js";

import type { Connection } from "../../lib/connection";
import { CoreController } from "../../lib/core-controller";
import { capitalize, formatCompact, formatDateTime } from "../../lib/format";
import type { ChatItem, Session } from "../../lib/types";
import { contextLabel, totalTokens } from "../../lib/usage";
import "../../ui/hca-badge";
import "../../ui/hca-banner";
import "../../ui/hca-button";
import "../../ui/hca-confirm-dialog";
import type { HcaConfirmDialog } from "../../ui/hca-confirm-dialog";
import "../../ui/hca-empty-state";
import "../../ui/hca-list-row";
import "../../ui/hca-page";
import "../../ui/hca-property-list";
import type { Property } from "../../ui/hca-property-list";
import "../../ui/hca-section";
import "../../ui/hca-sidebar-layout";
import "../../ui/hca-split";
import "../../ui/hca-tabs";
import type { Tab } from "../../ui/hca-tabs";
import "../chat/hca-message-list";

const DETAIL_TABS: Tab[] = [
  { id: "info", label: "Info" },
  { id: "messages", label: "Messages" },
];

const CHANNELS: Record<string, string> = { panel: "Chat panel", voice: "Voice" };

const onOff = (on: boolean) => (on ? "On" : "Off");
const tokens = (value: number | null): Pick<Property, "value" | "hint"> =>
  value === null ? { value: "–" } : { value: formatCompact(value), hint: value.toLocaleString() };

/**
 * Every session in a sidebar on the right; the selected one on the left, in two tabs: what is
 * known about it (the app's data and settings apart from what Claude Code reports) and its
 * messages.
 */
@customElement("hca-sessions-view")
export class HcaSessionsView extends LitElement {
  static styles = css`
    :host {
      display: block;
      height: 100%;
    }
    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: var(--hca-space-2);
    }
    hca-tabs {
      display: block;
      margin-bottom: var(--hca-space-2);
    }
  `;

  @property({ attribute: false }) connection!: Connection;
  @state() private sessions: Session[] = [];
  @state() private selected: string | null = null;
  @state() private detailTab = "info";
  @state() private history: ChatItem[] = [];
  @state() private error: string | null = null;
  @query("hca-confirm-dialog") private confirm!: HcaConfirmDialog;

  constructor() {
    super();
    new CoreController(this, {
      onOpen: () => this.load(),
      onEvent: (event) => {
        if (event.type === "session_updated") this.upsert(event.session);
        if (event.type === "session_deleted") this.forget(event.session_id);
        if (event.type === "turn_finished" && event.session_id === this.selected) this.loadHistory();
      },
    });
  }

  private async load(): Promise<void> {
    this.sessions = await this.connection.request<Session[]>("sessions/list");
    // After a reconnection the open session may have been deleted meanwhile.
    if (!this.sessions.some((s) => s.session_id === this.selected)) this.selected = null;
    if (!this.selected && this.sessions.length) await this.select(this.sessions[0]);
  }

  private upsert(session: Session): void {
    const others = this.sessions.filter((s) => s.session_id !== session.session_id);
    this.sessions = [session, ...others].sort((a, b) => b.last_activity.localeCompare(a.last_activity));
  }

  /** A deleted session leaves the list; if it was open, the newest one opens. */
  private forget(sessionId: string): void {
    this.sessions = this.sessions.filter((s) => s.session_id !== sessionId);
    if (this.selected !== sessionId) return;
    this.selected = null;
    this.history = [];
    if (this.sessions.length) this.select(this.sessions[0]);
  }

  private async select(session: Session): Promise<void> {
    this.selected = session.session_id;
    this.history = [];
    await this.loadHistory();
  }

  private async loadHistory(): Promise<void> {
    const sessionId = this.selected;
    if (!sessionId) return;
    const history = await this.connection.request<ChatItem[]>("sessions/history", { session_id: sessionId });
    // Another session may have been selected while this one loaded.
    if (this.selected === sessionId) this.history = history;
  }

  private async run(action: () => Promise<unknown>): Promise<void> {
    this.error = null;
    try {
      await action();
    } catch (err) {
      this.error = (err as Error).message;
    }
  }

  private end(session: Session): Promise<void> {
    return this.run(() => this.connection.request("sessions/close", { session_id: session.session_id }));
  }

  private async delete(session: Session): Promise<void> {
    const confirmed = await this.confirm.ask({
      heading: "Delete this session?",
      message: `"${session.title || "Session"}" and all its messages will be deleted for good. Long-term memory is not affected.`,
      confirmLabel: "Delete",
      danger: true,
    });
    if (confirmed) await this.run(() => this.connection.request("sessions/delete", { session_id: session.session_id }));
  }

  private renderRow(session: Session) {
    const total = totalTokens(session.claude);
    const date = formatDateTime(session.last_activity);
    const detail = total === null ? date : `${date}, ${formatCompact(total)} tokens used`;
    return html`
      <hca-list-row selectable heading=${session.title || "(no messages)"} detail=${detail}
        ?selected=${session.session_id === this.selected} @hca-select=${() => this.select(session)}>
        ${session.busy
          ? html`<hca-badge slot="end" tone="accent">Answering</hca-badge>`
          : session.active
            ? html`<hca-badge slot="end" tone="ok">Active</hca-badge>`
            : nothing}
      </hca-list-row>
    `;
  }

  /** The app's own data and the settings the session runs with. */
  private appProperties(session: Session): Property[] {
    const { settings } = session;
    const items: Property[] = [
      { label: "Session ID", value: session.session_id },
      { label: "User", value: session.source.name ?? session.source.key },
      { label: "Channel", value: CHANNELS[session.source.channel] ?? session.source.channel },
      { label: "Started", value: formatDateTime(session.created_at) },
      { label: "Last message", value: formatDateTime(session.last_activity) },
    ];
    if (session.closed_at) items.push({ label: "Ended", value: formatDateTime(session.closed_at) });
    items.push(
      { label: "Model", value: capitalize(settings.model) },
      { label: "Effort", value: capitalize(settings.effort) },
      { label: "Web search", value: onOff(settings.web_search) },
      { label: "Read files", value: onOff(settings.read_files) },
      { label: "Long-term memory", value: onOff(settings.memory_enabled) },
      { label: "MCP servers", value: settings.mcp_servers.join(", ") || "None" },
    );
    return items;
  }

  /** What Claude Code reported; the estimated cost is kept but not shown. */
  private claudeProperties(session: Session): Property[] {
    const { claude } = session;
    const exact = claude.context_tokens === null ? undefined
      : `${claude.context_tokens.toLocaleString()}${claude.context_window ? ` of ${claude.context_window.toLocaleString()}` : ""} tokens`;
    return [
      { label: "Claude session ID", value: claude.session_id ?? "–" },
      { label: "Context used", value: contextLabel(claude) ?? "–", hint: exact },
      { label: "Tokens used", ...tokens(totalTokens(claude)) },
      { label: "Input tokens", ...tokens(claude.input_tokens) },
      { label: "Output tokens", ...tokens(claude.output_tokens) },
      { label: "Read from cache", ...tokens(claude.cache_read_input_tokens) },
      { label: "Written to cache", ...tokens(claude.cache_creation_input_tokens) },
      { label: "Web searches", value: claude.web_search_requests === null ? "–" : String(claude.web_search_requests) },
    ];
  }

  private renderDetail(session: Session) {
    if (this.detailTab === "info") {
      return html`<hca-split role="tabpanel" aria-label="Info">
        <hca-property-list slot="start" .items=${this.appProperties(session)}></hca-property-list>
        <hca-property-list slot="end" .items=${this.claudeProperties(session)}></hca-property-list>
      </hca-split>`;
    }
    return html`<div role="tabpanel" aria-label="Messages">
      ${this.history.length
        ? html`<hca-message-list .items=${this.history} userName=${session.source.name ?? "User"}
            sessionId=${session.session_id}></hca-message-list>`
        : html`<hca-empty-state icon="chat" heading="No messages"></hca-empty-state>`}
    </div>`;
  }

  private renderSelected(session: Session) {
    return html`
      <hca-section heading=${session.title || "Session"}>
        <div slot="actions" class="actions">
          ${session.active && !session.busy
            ? html`<hca-button size="sm" variant="primary" @click=${() => this.end(session)}>End session</hca-button>`
            : nothing}
          <hca-button size="sm" variant="danger" icon="trash" ?disabled=${session.busy}
            title=${session.busy ? "Wait for the answer before deleting this session." : "Delete this session"}
            @click=${() => this.delete(session)}>Delete</hca-button>
        </div>
        <hca-tabs label="Session details" .tabs=${DETAIL_TABS} selected=${this.detailTab}
          @hca-select=${(e: CustomEvent<{ id: string }>) => (this.detailTab = e.detail.id)}></hca-tabs>
        ${this.renderDetail(session)}
      </hca-section>
    `;
  }

  render() {
    const selected = this.sessions.find((s) => s.session_id === this.selected);
    return html`
      <hca-sidebar-layout heading="Sessions">
        <hca-page>
          ${this.error ? html`<hca-banner tone="error">${this.error}</hca-banner>` : nothing}
          ${selected
            ? this.renderSelected(selected)
            : html`<hca-empty-state icon="history" heading=${this.sessions.length ? "Select a session" : "No sessions yet"}>
                ${this.sessions.length ? "Choose one on the right to read it." : "They appear here as soon as one starts."}
              </hca-empty-state>`}
        </hca-page>
        <div slot="sidebar">${this.sessions.map((s) => this.renderRow(s))}</div>
      </hca-sidebar-layout>
      <hca-confirm-dialog></hca-confirm-dialog>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-sessions-view": HcaSessionsView;
  }
}
