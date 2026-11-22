import { LitElement, css, html, nothing } from "lit";
import { customElement, property } from "lit/decorators.js";

import "./hca-icon";
import { base } from "./styles";

/** A notice in the flow of a page: info, ok, warn or error, with an optional heading. */
@customElement("hca-banner")
export class HcaBanner extends LitElement {
  static styles = [
    base,
    css`
      :host {
        display: flex;
        gap: var(--hca-space-3);
        padding: var(--hca-space-3) var(--hca-space-4);
        border-radius: var(--hca-radius-sm);
        border: 1px solid var(--hca-border);
        background: var(--hca-surface-muted);
        font-size: var(--hca-text-sm);
        line-height: 1.45;
        --hca-icon-size: 18px;
      }
      :host([tone="ok"]) {
        background: var(--hca-ok-soft);
        border-color: transparent;
        color: var(--hca-ok);
      }
      :host([tone="warn"]) {
        background: var(--hca-warn-soft);
        border-color: transparent;
        color: var(--hca-warn);
      }
      :host([tone="error"]) {
        background: var(--hca-error-soft);
        border-color: transparent;
        color: var(--hca-error);
      }
      strong {
        display: block;
        margin-bottom: 2px;
      }
      .text {
        flex: 1;
        min-width: 0;
        color: var(--hca-text);
      }
    `,
  ];

  @property({ reflect: true }) tone: "info" | "ok" | "warn" | "error" = "info";
  @property() heading = "";

  render() {
    const icon = { info: "chat", ok: "check", warn: "alert", error: "alert" }[this.tone];
    return html`
      <hca-icon name=${icon}></hca-icon>
      <div class="text" role=${this.tone === "error" ? "alert" : "status"}>
        ${this.heading ? html`<strong>${this.heading}</strong>` : nothing}
        <slot></slot>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-banner": HcaBanner;
  }
}
