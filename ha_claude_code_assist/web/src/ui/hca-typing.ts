import { LitElement, css, html } from "lit";
import { customElement } from "lit/decorators.js";

/** Three pulsing dots: the assistant is writing. */
@customElement("hca-typing")
export class HcaTyping extends LitElement {
  static styles = css`
    :host {
      display: inline-flex;
      gap: 4px;
      margin-top: var(--hca-space-3);
    }
    span {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: var(--hca-text-muted);
      animation: pulse 1.2s infinite ease-in-out both;
    }
    span:nth-child(2) {
      animation-delay: 0.2s;
    }
    span:nth-child(3) {
      animation-delay: 0.4s;
    }
    @keyframes pulse {
      0%,
      80%,
      100% {
        opacity: 0.25;
      }
      40% {
        opacity: 1;
      }
    }
    @media (prefers-reduced-motion: reduce) {
      span {
        animation: none;
        opacity: 0.6;
      }
    }
  `;

  render() {
    return html`<span></span><span></span><span></span>`;
  }

  connectedCallback(): void {
    super.connectedCallback();
    this.setAttribute("role", "status");
    this.setAttribute("aria-label", "The assistant is writing");
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-typing": HcaTyping;
  }
}
