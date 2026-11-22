import { LitElement, css, html } from "lit";
import { customElement, property } from "lit/decorators.js";

import { base } from "./styles";

/** A short state label: neutral, accent, ok, warn or error. */
@customElement("hca-badge")
export class HcaBadge extends LitElement {
  static styles = [
    base,
    css`
      :host {
        display: inline-flex;
        align-items: center;
        gap: var(--hca-space-1);
        padding: 2px var(--hca-space-2);
        border-radius: var(--hca-radius-full);
        font-size: var(--hca-text-xs);
        font-weight: 600;
        white-space: nowrap;
        background: var(--hca-surface-muted);
        color: var(--hca-text-muted);
        --hca-icon-size: 12px;
      }
      :host([tone="accent"]) {
        background: var(--hca-accent-soft);
        color: var(--hca-accent);
      }
      :host([tone="ok"]) {
        background: var(--hca-ok-soft);
        color: var(--hca-ok);
      }
      :host([tone="warn"]) {
        background: var(--hca-warn-soft);
        color: var(--hca-warn);
      }
      :host([tone="error"]) {
        background: var(--hca-error-soft);
        color: var(--hca-error);
      }
    `,
  ];

  @property({ reflect: true }) tone: "neutral" | "accent" | "ok" | "warn" | "error" = "neutral";

  render() {
    return html`<slot></slot>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-badge": HcaBadge;
  }
}
