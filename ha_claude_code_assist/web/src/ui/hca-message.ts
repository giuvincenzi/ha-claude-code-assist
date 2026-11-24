import { LitElement, css, html, nothing } from "lit";
import { customElement, property } from "lit/decorators.js";

import "./hca-markdown";
import { base } from "./styles";

/**
 * One message of a chat: from the user (plain text in a bubble on the right, as it was written)
 * or from the assistant (markdown on the left). `meta` above it, `footer` below, both small and
 * grey; what comes with the message, such as attached files, goes in slot "before", above the text.
 */
@customElement("hca-message")
export class HcaMessage extends LitElement {
  static styles = [
    base,
    css`
      :host {
        display: flex;
        flex-direction: column;
        align-items: flex-start;
      }
      :host([from="user"]) {
        align-items: flex-end;
      }
      .meta,
      .footer {
        font-size: var(--hca-text-xs);
        color: var(--hca-text-muted);
      }
      .meta {
        margin: var(--hca-space-4) 0 var(--hca-space-1);
      }
      .footer {
        margin-top: var(--hca-space-1);
      }
      hca-markdown {
        max-width: 100%;
      }
      .text {
        max-width: 85%;
        white-space: pre-wrap;
        word-break: break-word;
        padding: var(--hca-space-2) var(--hca-space-4);
        border-radius: var(--hca-radius-lg) var(--hca-radius-lg) var(--hca-radius-sm) var(--hca-radius-lg);
        background: var(--hca-accent-soft);
        line-height: 1.5;
      }
    `,
  ];

  @property({ reflect: true }) from: "user" | "assistant" = "assistant";
  @property() text = "";
  @property() meta = "";
  @property() footer = "";

  render() {
    return html`
      ${this.meta ? html`<div class="meta">${this.meta}</div>` : nothing}
      <slot name="before"></slot>
      ${this.from === "assistant"
        ? html`<hca-markdown text=${this.text}></hca-markdown>`
        : this.text ? html`<div class="text">${this.text}</div>` : nothing}
      ${this.footer ? html`<div class="footer">${this.footer}</div>` : nothing}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-message": HcaMessage;
  }
}
