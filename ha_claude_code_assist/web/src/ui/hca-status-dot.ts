import { LitElement, css, html, nothing } from "lit";
import { customElement, property } from "lit/decorators.js";

import { base } from "./styles";

/**
 * A small dot that tells a state at a glance, as "online" does: ok (green), accent (blue, pulsing,
 * for something in progress), or none, which keeps its place empty so things stay aligned.
 * `label` names the state, as tooltip and for screen readers.
 */
@customElement("hca-status-dot")
export class HcaStatusDot extends LitElement {
  static styles = [
    base,
    css`
      :host {
        display: inline-flex;
      }
      span {
        width: 8px;
        height: 8px;
        border-radius: 50%;
      }
      :host([tone="ok"]) span {
        background: var(--hca-ok);
      }
      :host([tone="accent"]) span {
        background: var(--hca-accent);
        animation: pulse 1.4s ease-in-out infinite;
      }
      @keyframes pulse {
        50% {
          opacity: 0.35;
        }
      }
      @media (prefers-reduced-motion: reduce) {
        :host([tone="accent"]) span {
          animation: none;
        }
      }
    `,
  ];

  @property({ reflect: true }) tone: "none" | "ok" | "accent" = "none";
  @property() label = "";

  render() {
    return html`<span role=${this.label ? "img" : nothing} aria-label=${this.label || nothing}
      title=${this.label || nothing}></span>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-status-dot": HcaStatusDot;
  }
}
