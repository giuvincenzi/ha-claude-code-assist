import { LitElement, css, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";

import "./hca-icon";
import { base } from "./styles";

/**
 * One attached file as a square tile: the picture, or an icon with the file's name and type.
 * While it is not ready (a picture still loading, a file still uploading) it shows a shimmering
 * placeholder. Once ready, a click opens it (fires `hca-open`). With `removable`, a button
 * removes it (fires `hca-remove`).
 */
@customElement("hca-attachment")
export class HcaAttachment extends LitElement {
  static styles = [
    base,
    css`
      :host {
        position: relative;
        display: block;
        flex: none;
        width: var(--hca-attachment-size);
        height: var(--hca-attachment-size);
        border: 1px solid var(--hca-border);
        border-radius: var(--hca-radius);
        background: var(--hca-surface-muted);
        overflow: hidden;
      }
      :host([failed]) {
        border-color: var(--hca-error);
      }
      .open {
        display: block;
        width: 100%;
        height: 100%;
        padding: 0;
        border: none;
        background: none;
        color: inherit;
        font: inherit;
        cursor: zoom-in;
      }
      .open.file-tile {
        cursor: pointer;
      }
      img {
        display: block;
        width: 100%;
        height: 100%;
        object-fit: cover;
      }
      .file {
        display: grid;
        align-content: center;
        justify-items: center;
        gap: var(--hca-space-1);
        height: 100%;
        padding: var(--hca-space-2);
        text-align: center;
        color: var(--hca-text-muted);
        --hca-icon-size: 28px;
      }
      .name {
        max-width: 100%;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        font-size: var(--hca-text-xs);
        color: var(--hca-text);
      }
      .type {
        font-size: var(--hca-text-xs);
        letter-spacing: 0.04em;
      }
      .skeleton {
        position: absolute;
        inset: 0;
        background: linear-gradient(100deg, transparent 30%, var(--hca-border) 50%, transparent 70%)
          var(--hca-surface-muted);
        background-size: 250% 100%;
        animation: shimmer 1.4s ease-in-out infinite;
      }
      @keyframes shimmer {
        from {
          background-position: 120% 0;
        }
        to {
          background-position: -120% 0;
        }
      }
      @media (prefers-reduced-motion: reduce) {
        .skeleton {
          animation: none;
        }
      }
      .remove {
        position: absolute;
        top: var(--hca-space-1);
        right: var(--hca-space-1);
        display: grid;
        place-items: center;
        width: 24px;
        height: 24px;
        padding: 0;
        border: none;
        border-radius: var(--hca-radius-full);
        background: var(--hca-surface);
        color: var(--hca-text);
        box-shadow: var(--hca-shadow);
        cursor: pointer;
        opacity: 0;
        transition: opacity 0.15s;
        --hca-icon-size: 14px;
      }
      :host(:hover) .remove,
      .remove:focus-visible {
        opacity: 1;
      }
      /* Touch screens have no hover: the button is always there. */
      @media (hover: none) {
        .remove {
          opacity: 1;
        }
      }
    `,
  ];

  @property() name = "";
  /** The picture to show; none for a file that is not a picture. */
  @property() src = "";
  /** Still uploading: the placeholder stays until it is false. */
  @property({ type: Boolean }) loading = false;
  @property({ type: Boolean, reflect: true }) failed = false;
  @property({ type: Boolean }) removable = false;
  @state() private pictureLoaded = false;

  protected willUpdate(changed: Map<string, unknown>): void {
    if (changed.has("src")) this.pictureLoaded = false;
  }

  private renderContent() {
    if (this.src && !this.failed) {
      return html`<img src=${this.src} alt=${this.name} @load=${() => (this.pictureLoaded = true)}
        @error=${() => (this.failed = true)}>`;
    }
    const type = this.name.includes(".") ? this.name.split(".").pop()!.toUpperCase() : "FILE";
    return html`<div class="file" title=${this.name}>
      <hca-icon name=${this.failed ? "alert" : "file"}></hca-icon>
      <span class="name">${this.name}</span>
      <span class="type">${type}</span>
    </div>`;
  }

  render() {
    const waiting = this.loading || (Boolean(this.src) && !this.pictureLoaded && !this.failed);
    const content = this.renderContent();
    return html`
      ${this.loading || this.failed
        ? content
        : html`<button type="button" class="open ${this.src ? "" : "file-tile"}"
            aria-label=${this.src ? `Open ${this.name}` : `Download ${this.name}`}
            @click=${() => this.dispatchEvent(new CustomEvent("hca-open", { bubbles: true, composed: true }))}>${content}</button>`}
      ${waiting ? html`<div class="skeleton" aria-label="Loading"></div>` : nothing}
      ${this.removable
        ? html`<button type="button" class="remove" aria-label=${`Remove ${this.name}`} title="Remove"
            @click=${() => this.dispatchEvent(new CustomEvent("hca-remove", { bubbles: true, composed: true }))}>
            <hca-icon name="x"></hca-icon></button>`
        : nothing}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-attachment": HcaAttachment;
  }
}
