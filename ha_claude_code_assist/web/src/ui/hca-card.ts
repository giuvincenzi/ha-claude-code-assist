import { LitElement, css, html } from "lit";
import { customElement } from "lit/decorators.js";

import { base } from "./styles";

/** A bordered box inside a section, for one item of a list (an MCP server, for example). */
@customElement("hca-card")
export class HcaCard extends LitElement {
  static styles = [
    base,
    css`
      :host {
        display: grid;
        gap: var(--hca-space-3);
        padding: var(--hca-space-4);
        border: 1px solid var(--hca-border);
        border-radius: var(--hca-radius);
        background: var(--hca-surface);
      }
    `,
  ];

  render() {
    return html`<slot></slot>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-card": HcaCard;
  }
}
