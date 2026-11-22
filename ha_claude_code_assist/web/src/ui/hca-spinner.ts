import { LitElement, css, html } from "lit";
import { customElement } from "lit/decorators.js";

/** An indeterminate progress ring, the size of the text around it. */
@customElement("hca-spinner")
export class HcaSpinner extends LitElement {
  static styles = css`
    :host {
      display: inline-block;
      width: var(--hca-icon-size, 16px);
      height: var(--hca-icon-size, 16px);
    }
    span {
      display: block;
      width: 100%;
      height: 100%;
      border: 2px solid currentColor;
      border-right-color: transparent;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    @keyframes spin {
      to {
        transform: rotate(360deg);
      }
    }
    @media (prefers-reduced-motion: reduce) {
      span {
        animation-duration: 2.4s;
      }
    }
  `;

  render() {
    return html`<span role="status" aria-label="Loading"></span>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-spinner": HcaSpinner;
  }
}
