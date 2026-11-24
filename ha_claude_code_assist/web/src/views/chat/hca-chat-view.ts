import { LitElement, css, html, nothing } from "lit";
import { customElement, property, query, state } from "lit/decorators.js";

import type { Connection } from "../../lib/connection";
import { MAX_ATTACHMENT_BYTES, TOO_LARGE, uploadAttachment } from "../../lib/attachments";
import { applyClaudeEvent, currentConversationId, newConversationId } from "../../lib/conversation";
import { CoreController } from "../../lib/core-controller";
import { capitalize, formatCompact } from "../../lib/format";
import { contextPercent } from "../../lib/usage";
import { loadSettings } from "../../lib/settings";
import type { ChatAttachment, ChatItem, CoreEvent, Session, SettingsView } from "../../lib/types";
import "../../ui/hca-banner";
import "../../ui/hca-button";
import "../../ui/hca-composer";
import "../../ui/hca-drop-zone";
import type { HcaComposer } from "../../ui/hca-composer";
import "../../ui/hca-empty-state";
import "../../ui/hca-page";
import "../../ui/hca-toolbar";
import "./hca-message-list";

/**
 * Chat with the assistant, streamed live. A new conversation shows the composer in the middle of
 * the page; with the first message it moves down to its place under the conversation. Nothing is
 * shown until the core says whether this browser's conversation is still going, so the composer
 * never starts in the wrong place.
 */
@customElement("hca-chat-view")
export class HcaChatView extends LitElement {
  static styles = css`
    :host {
      display: block;
      height: 100%;
    }
    .chat {
      display: flex;
      flex-direction: column;
      height: 100%;
    }
    .conversation {
      flex: 1 1 0;
      min-height: 0;
      overflow-y: auto;
    }
    .dock {
      flex: none;
    }
    .dock hca-page {
      padding-top: var(--hca-space-2);
      padding-bottom: var(--hca-space-4);
    }
    .spacer {
      flex: 0 1 0;
    }
    /* New conversation: the composer sits between two equal spaces, in the middle. With the
       first message the spaces shrink and the conversation grows: the composer slides down.
       Only then ("sliding"): a conversation shown again is already in its place. */
    .sliding .conversation,
    .sliding .spacer {
      transition: flex-grow 0.45s ease;
    }
    .new .spacer {
      flex-grow: 1;
    }
    .new .conversation {
      flex-grow: 0;
    }
    /* Stays above the conversation: only the messages scroll. */
    .top {
      flex: none;
    }
    .top hca-page {
      padding-top: var(--hca-space-2);
      padding-bottom: var(--hca-space-2);
    }
    .conversation hca-page {
      padding-top: 0;
    }
    @media (prefers-reduced-motion: reduce) {
      .sliding .conversation,
      .sliding .spacer {
        transition: none;
      }
    }
  `;

  @property({ attribute: false }) connection!: Connection;
  @state() private items: ChatItem[] = [];
  @state() private session: Session | null = null;
  @state() private busy = false;
  @state() private error: string | null = null;
  /** The core has answered whether this browser's conversation is still going. */
  @state() private loaded = false;
  /** The composer is moving down after the first message of a new conversation. */
  @state() private sliding = false;
  @query(".conversation") private scroller?: HTMLElement;
  @query("hca-composer") private composer!: HcaComposer;
  @state() private settings: SettingsView | null = null;
  private conversationId = currentConversationId();

  constructor() {
    super();
    new CoreController(this, {
      onOpen: () => Promise.all([this.restore(), this.loadSettings()]),
      onEvent: (event) => this.onCoreEvent(event),
    });
  }

  private async loadSettings(): Promise<void> {
    this.settings = await loadSettings(this.connection);
  }

  /** A new conversation: nothing written yet and no session behind it. */
  private get isNew(): boolean {
    return this.items.length === 0 && !this.session;
  }

  /** Shows this browser's conversation if its session is still active. */
  private async restore(): Promise<void> {
    this.sliding = false;
    try {
      const sessions = await this.connection.request<Session[]>("sessions/list");
      const session = sessions.find((s) => s.active && s.conversation_ids.includes(this.conversationId)) ?? null;
      this.session = session;
      this.busy = session?.busy ?? false;
      this.items = session
        ? await this.connection.request<ChatItem[]>("sessions/history", { session_id: session.session_id })
        : [];
    } catch (err) {
      this.error = (err as Error).message;
    } finally {
      this.loaded = true;
    }
  }

  /** Whether files can be attached: the session's Read files setting, or the current one for a
   * new session. */
  private get attachable(): boolean {
    return (this.session ? this.session.settings.read_files : this.settings?.values.read_files) ?? false;
  }

  /** Why files cannot be attached, for the paperclip and the drop frame. */
  private get notAttachable(): string {
    return this.session
      ? "This session cannot open files. Turn on Read files in Tools, then start a new session."
      : "Turn on Read files in Tools to attach files.";
  }

  /**
   * Sends a message. Its files first go into the session's folder (the session is created if
   * needed), one HTTP request each; then the message. If anything fails, the message goes back
   * into the composer with its files, and a session left without messages is deleted.
   */
  private async send(text: string, files: File[]): Promise<void> {
    this.error = null;
    this.busy = true;
    this.sliding = this.isNew;
    const previews: ChatAttachment[] = files.map((file) => ({
      name: file.name, image: file.type.startsWith("image/"), loading: true,
      url: file.type.startsWith("image/") ? URL.createObjectURL(file) : undefined,
    }));
    let shown: ChatItem = { kind: "user", text, timestamp: new Date().toISOString(), ...(files.length ? { attachments: previews } : {}) };
    this.items = [...this.items, shown];
    let prepared: { session_id: string; empty: boolean } | null = null;
    try {
      const names: string[] = [];
      if (files.length) {
        prepared = await this.connection.request<{ session_id: string; empty: boolean }>("chat/prepare", {
          conversation_id: this.conversationId,
        });
        for (const file of files) names.push(await uploadAttachment(prepared.session_id, file));
        const sent: ChatItem = { ...shown, attachments: previews.map((p) => ({ ...p, loading: false })) };
        this.items = this.items.map((item) => (item === shown ? sent : item));
        shown = sent;
      }
      const { session_id } = await this.connection.request<{ session_id: string }>("chat/send", {
        conversation_id: this.conversationId,
        text,
        attachments: names,
      });
      if (this.session?.session_id !== session_id) {
        const sessions = await this.connection.request<Session[]>("sessions/list");
        this.session = sessions.find((s) => s.session_id === session_id) ?? null;
      }
    } catch (err) {
      this.busy = false;
      this.error = (err as Error).message;
      this.items = this.items.filter((item) => item !== shown);
      for (const p of previews) if (p.url) URL.revokeObjectURL(p.url);
      if (prepared?.empty) {
        await this.connection.request("sessions/delete", { session_id: prepared.session_id }).catch(() => undefined);
      }
      this.composer.restore(text, files);
    }
  }

  private async newConversation(): Promise<void> {
    // Close the current session: the next message from this user would otherwise continue it.
    if (this.session?.active) {
      try {
        await this.connection.request("sessions/close", { session_id: this.session.session_id });
      } catch (err) {
        this.error = (err as Error).message;
        return;
      }
    }
    this.startOver();
  }

  /** An empty new conversation in this browser. */
  private startOver(): void {
    // The previews made in the browser for the messages sent are not needed any more.
    for (const item of this.items) {
      if (item.kind === "user") for (const a of item.attachments ?? []) if (a.url) URL.revokeObjectURL(a.url);
    }
    this.conversationId = newConversationId();
    this.sliding = false;
    this.session = null;
    this.items = [];
    this.busy = false;
    this.error = null;
  }

  private onCoreEvent(event: CoreEvent): void {
    if (event.type === "session_updated") {
      if (event.session.session_id === this.session?.session_id) this.session = event.session;
      return;
    }
    // Read files may have changed, which decides whether a new session takes attachments.
    if (event.type === "settings_changed") {
      this.loadSettings();
      return;
    }
    // Deleted from Sessions (here or on another device): this chat starts over.
    if (event.type === "session_deleted") {
      if (event.session_id === this.session?.session_id) this.startOver();
      return;
    }
    if (event.type === "memory_changed" || event.type === "status_changed") return;
    if (event.session_id !== this.session?.session_id) return;
    if (event.type === "turn_event") this.items = applyClaudeEvent(this.items, event.event);
    if (event.type === "turn_finished") {
      this.busy = false;
      if (event.is_error) this.items = [...this.items, { kind: "error", text: event.text, timestamp: new Date().toISOString() }];
    }
  }

  protected updated(): void {
    this.scroller?.scrollTo({ top: this.scroller.scrollHeight });
  }

  /** The slide is over (children's own transitions bubble here too and are ignored). */
  private onTransitionEnd(event: TransitionEvent): void {
    if (event.propertyName === "flex-grow") this.sliding = false;
  }

  private renderToolbar() {
    return html`
      <div class="top">
        <hca-page width="narrow">
          <hca-toolbar>
            <hca-button slot="end" size="sm" icon="plus" ?disabled=${this.busy} @click=${this.newConversation}>
              New session
            </hca-button>
          </hca-toolbar>
        </hca-page>
      </div>
    `;
  }

  /** Model, effort and how full the context is, under the composer. */
  private renderInfo() {
    const s = this.session;
    if (!s) return nothing;
    const { settings, claude } = s;
    const percent = contextPercent(claude);
    const model = `${capitalize(settings.model)} with ${settings.effort} effort`;
    const text = percent !== null
      ? `${model}, ${percent}% of the context used`
      : claude.context_tokens !== null ? `${model}, ${formatCompact(claude.context_tokens)} tokens of context used` : model;
    const hint = claude.context_tokens === null ? ""
      : `The context uses ${claude.context_tokens.toLocaleString()}${claude.context_window ? ` of ${claude.context_window.toLocaleString()}` : ""} tokens.`;
    return html`<span slot="info" title=${hint}>${text}</span>`;
  }

  render() {
    if (!this.loaded) return nothing;
    const open = this.connection.state === "open";
    return html`
      <div class="chat ${this.isNew ? "new" : ""} ${this.sliding ? "sliding" : ""}"
        @transitionend=${this.onTransitionEnd}>
        ${this.isNew ? nothing : this.renderToolbar()}
        <div class="spacer"></div>
        <div class="conversation">
          ${this.isNew
            ? nothing
            : html`<hca-page width="narrow">
                <hca-message-list .items=${this.items} .busy=${this.busy}
                  userName=${this.session?.source.name ?? "You"} sessionId=${this.session?.session_id ?? ""}></hca-message-list>
              </hca-page>`}
        </div>
        <div class="dock">
          <hca-page width="narrow">
            ${this.isNew
              ? html`<hca-empty-state icon="chat" heading="How can I help?">
                  Ask about your home or anything else.
                </hca-empty-state>`
              : nothing}
            ${this.error ? html`<hca-banner tone="error">${this.error}</hca-banner>` : nothing}
            <hca-composer placeholder="Message HA Claude Code Assist" ?disabled=${this.busy || !open}
              ?attachable=${this.attachable} maxBytes=${MAX_ATTACHMENT_BYTES} tooLarge=${TOO_LARGE}
              notAttachable=${this.notAttachable}
              @hca-send=${(e: CustomEvent<{ text: string; files: File[] }>) => this.send(e.detail.text, e.detail.files)}>
              ${this.renderInfo()}</hca-composer>
          </hca-page>
        </div>
        <div class="spacer"></div>
      </div>
      <hca-drop-zone message="Images, PDFs and text files, up to 16 MB each." ?disabled=${!this.attachable}
        reason=${this.notAttachable}
        @hca-drop=${(e: CustomEvent<{ files: File[] }>) => this.composer.attach(e.detail.files)}></hca-drop-zone>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-chat-view": HcaChatView;
  }
}
