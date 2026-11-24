import { LitElement, css, html, nothing } from "lit";
import { customElement, property } from "lit/decorators.js";

import { base } from "./styles";

/**
 * A page of settings: its content scrolls above a bar that always stays at the bottom, with the
 * page's buttons on the right (slot "actions") and a message on the left: what was saved, what
 * went wrong or what is not saved yet. The bar is outside the scrolling content, so it never
 * covers it.
 */
@customElement("hca-form-layout")
export class HcaFormLayout extends LitElement {
  static styles = [
    base,
    css`
      :host {
        display: flex;
        flex-direction: column;
        height: 100%;
      }
      .content {
        flex: 1;
        min-height: 0;
        overflow-y: auto;
      }
      .bar {
        border-top: 1px solid var(--hca-border);
        background: var(--hca-surface);
      }
      /* As wide as the page above it, so the buttons line up with its content. */
      .inner {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        justify-content: flex-end;
        gap: var(--hca-space-3);
        max-width: var(--hca-page-width);
        margin: 0 auto;
        padding: var(--hca-space-3) var(--hca-space-4);
      }
      .message {
        flex: 1 1 240px;
        min-width: 0;
        font-size: var(--hca-text-sm);
        line-height: 1.45;
        color: var(--hca-text-muted);
      }
      :host([tone="ok"]) .message {
        color: var(--hca-ok);
      }
      :host([tone="error"]) .message {
        color: var(--hca-error);
      }
      .actions {
        display: flex;
        gap: var(--hca-space-2);
      }
    `,
  ];

  @property() message = "";
  @property({ reflect: true }) tone: "neutral" | "ok" | "error" = "neutral";

  render() {
    return html`
      <div class="content"><slot></slot></div>
      <div class="bar">
        <div class="inner">
          <div class="message" role=${this.tone === "error" ? "alert" : "status"}>${this.message || nothing}</div>
          <div class="actions"><slot name="actions"></slot></div>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-form-layout": HcaFormLayout;
  }
}
