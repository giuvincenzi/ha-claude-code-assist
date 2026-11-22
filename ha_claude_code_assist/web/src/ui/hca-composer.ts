import { LitElement, css, html, nothing } from "lit";
import { customElement, property, query, state } from "lit/decorators.js";

import { saveFile } from "../lib/files";
import "./hca-attachment";
import "./hca-icon-button";
import "./hca-lightbox";
import type { HcaLightbox } from "./hca-lightbox";
import { base } from "./styles";

const MAX_HEIGHT = 200;

interface Pending {
  id: number;
  file: File;
  /** A picture's preview, made in the browser; the file is not sent anywhere yet. */
  url: string;
}

/**
 * Where the message is written: grows with the text, Enter sends, Shift+Enter starts a new line.
 * With `attachable`, files can be attached (pasted, chosen with the paperclip, or given with
 * `attach`, for files dropped on the page); they stay in the browser until the message is sent,
 * and a click opens them. Files over `maxBytes` are refused with `tooLarge`, a sentence that
 * names the file.
 *
 * Fires `hca-send` with `detail.text` and `detail.files`. Slot "info": small facts on the right
 * of the hint line.
 */
@customElement("hca-composer")
export class HcaComposer extends LitElement {
  static styles = [
    base,
    css`
      .box {
        display: grid;
        gap: var(--hca-space-2);
        padding: var(--hca-space-2);
        border: 1px solid var(--hca-border-strong);
        border-radius: var(--hca-radius-lg);
        background: var(--hca-surface);
        box-shadow: var(--hca-shadow);
        transition: border-color 0.15s, box-shadow 0.15s;
      }
      .box:focus-within {
        border-color: var(--hca-accent);
        box-shadow: var(--hca-focus);
      }
      .attachments {
        display: flex;
        flex-wrap: wrap;
        gap: var(--hca-space-2);
        padding: var(--hca-space-1) var(--hca-space-1) 0;
      }
      .row {
        display: flex;
        align-items: flex-end;
        gap: var(--hca-space-2);
      }
      textarea {
        flex: 1;
        min-height: 24px;
        max-height: ${MAX_HEIGHT}px;
        margin: 6px 0;
        padding: 0;
        border: none;
        outline: none;
        resize: none;
        background: transparent;
        color: var(--hca-text);
        font: inherit;
        font-size: var(--hca-text-md);
        line-height: 1.5;
      }
      textarea:focus-visible {
        box-shadow: none;
      }
      input[type="file"] {
        display: none;
      }
      .hint {
        display: flex;
        flex-wrap: wrap;
        justify-content: space-between;
        gap: 0 var(--hca-space-3);
        margin: var(--hca-space-1) var(--hca-space-4) 0;
        font-size: var(--hca-text-xs);
        color: var(--hca-text-muted);
      }
      .refused {
        margin: var(--hca-space-1) var(--hca-space-4) 0;
        font-size: var(--hca-text-xs);
        color: var(--hca-error);
      }
    `,
  ];

  @property({ type: Boolean }) disabled = false;
  @property() placeholder = "Message";
  @property({ type: Boolean }) attachable = false;
  /** Why files cannot be attached, shown on the paperclip when `attachable` is false. */
  @property() notAttachable = "";
  @property({ type: Number }) maxBytes = Infinity;
  /** The sentence for a file over `maxBytes`; `{name}` is replaced by the file's name. */
  @property() tooLarge = "{name} is too large.";
  @state() private pending: Pending[] = [];
  @state() private refused: string[] = [];
  @query("textarea") private textarea!: HTMLTextAreaElement;
  @query("input[type=file]") private picker!: HTMLInputElement;
  @query("hca-lightbox") private lightbox!: HcaLightbox;
  private nextId = 1;

  override focus(): void {
    this.textarea?.focus();
  }

  /** Puts a message back, files included, when it could not be sent. */
  restore(text: string, files: File[]): void {
    this.textarea.value = text;
    this.resize();
    this.attach(files);
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    for (const p of this.pending) URL.revokeObjectURL(p.url);
  }

  /** Adds files to the message (refusing those over `maxBytes`). */
  attach(files: Iterable<File>): void {
    if (!this.attachable) return;
    const accepted: Pending[] = [];
    const refused: string[] = [];
    for (const file of files) {
      if (file.size > this.maxBytes) refused.push(this.tooLarge.replace("{name}", file.name));
      else accepted.push({ id: this.nextId++, file, url: file.type.startsWith("image/") ? URL.createObjectURL(file) : "" });
    }
    this.pending = [...this.pending, ...accepted];
    this.refused = refused;
  }

  /** A picture opens over the page; another file is saved, as it would be once sent. */
  private openPending(p: Pending): void {
    if (p.url) {
      this.lightbox.show(p.url, p.file.name, p.url);
      return;
    }
    const url = URL.createObjectURL(p.file);
    saveFile(url, p.file.name);
    URL.revokeObjectURL(url);
  }

  private removePending(id: number): void {
    const gone = this.pending.find((p) => p.id === id);
    if (gone?.url) URL.revokeObjectURL(gone.url);
    this.pending = this.pending.filter((p) => p.id !== id);
  }

  private resize(): void {
    this.textarea.style.height = "auto";
    this.textarea.style.height = `${Math.min(this.textarea.scrollHeight, MAX_HEIGHT)}px`;
  }

  private send(): void {
    const text = this.textarea.value.trim();
    if ((!text && !this.pending.length) || this.disabled) return;
    const files = this.pending.map((p) => p.file);
    this.dispatchEvent(new CustomEvent("hca-send", { detail: { text, files }, bubbles: true, composed: true }));
    for (const p of this.pending) URL.revokeObjectURL(p.url);
    this.pending = [];
    this.refused = [];
    this.textarea.value = "";
    this.resize();
  }

  private onKeydown(event: KeyboardEvent): void {
    if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      this.send();
    }
  }

  private onPaste(event: ClipboardEvent): void {
    const files = Array.from(event.clipboardData?.files ?? []);
    if (!files.length || !this.attachable) return;
    event.preventDefault();
    this.attach(files);
  }

  private onPicked(): void {
    this.attach(Array.from(this.picker.files ?? []));
    this.picker.value = "";
  }

  render() {
    return html`
      <div class="box">
        ${this.pending.length
          ? html`<div class="attachments">
              ${this.pending.map((p) => html`<hca-attachment name=${p.file.name} src=${p.url} removable
                @hca-open=${() => this.openPending(p)} @hca-remove=${() => this.removePending(p.id)}></hca-attachment>`)}
            </div>`
          : nothing}
        <div class="row">
          <hca-icon-button icon="paperclip" ?disabled=${!this.attachable || this.disabled}
            label=${this.attachable ? "Attach files" : this.notAttachable || "Attach files"}
            @click=${() => this.picker.click()}></hca-icon-button>
          <input type="file" multiple @change=${this.onPicked}>
          <textarea rows="1" aria-label=${this.placeholder} placeholder=${this.placeholder}
            @input=${this.resize} @keydown=${this.onKeydown} @paste=${this.onPaste}></textarea>
          <hca-icon-button variant="primary" icon="send" label="Send" ?disabled=${this.disabled}
            @click=${this.send}></hca-icon-button>
        </div>
      </div>
      ${this.refused.map((text) => html`<div class="refused" role="alert">${text}</div>`)}
      <div class="hint"><span>Enter to send, Shift+Enter for a new line</span><slot name="info"></slot></div>
      <hca-lightbox></hca-lightbox>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-composer": HcaComposer;
  }
}
