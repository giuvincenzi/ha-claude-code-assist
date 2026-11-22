import { LitElement, css, html } from "lit";
import { customElement } from "lit/decorators.js";

/** Something the user types, such as a command, inside a sentence. */
@customElement("hca-code")
export class HcaCode extends LitElement {
  static styles = css`
    :host {
      padding: 1px 5px;
      border-radius: var(--hca-radius-sm);
      background: var(--hca-surface-muted);
      color: var(--hca-text);
      font-family: var(--hca-font-mono);
      font-size: 0.95em;
      white-space: nowrap;
    }
  `;

  render() {
    return html`<slot></slot>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-code": HcaCode;
  }
}
