import { LitElement, css, html } from "lit";
import { customElement } from "lit/decorators.js";

import { base } from "./styles";

/** A thin bar above some content: small grey text on the left (default slot), actions on the right (slot "end"). */
@customElement("hca-toolbar")
export class HcaToolbar extends LitElement {
  static styles = [
    base,
    css`
      :host {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        justify-content: space-between;
        gap: var(--hca-space-1) var(--hca-space-3);
        font-size: var(--hca-text-xs);
        color: var(--hca-text-muted);
      }
      .start {
        min-width: 0;
      }
    `,
  ];

  render() {
    return html`<div class="start"><slot></slot></div><slot name="end"></slot>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-toolbar": HcaToolbar;
  }
}
