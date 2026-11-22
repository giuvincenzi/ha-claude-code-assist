import { LitElement, css, html } from "lit";
import { customElement, property } from "lit/decorators.js";

import "./hca-icon";
import type { IconName } from "./hca-icon";
import { base } from "./styles";

/** What a page or list shows when there is nothing yet: an icon, a heading and a short text. */
@customElement("hca-empty-state")
export class HcaEmptyState extends LitElement {
  static styles = [
    base,
    css`
      :host {
        display: grid;
        justify-items: center;
        gap: var(--hca-space-2);
        padding: var(--hca-space-6) var(--hca-space-4);
        text-align: center;
        color: var(--hca-text-muted);
        --hca-icon-size: 28px;
      }
      h3 {
        margin: var(--hca-space-1) 0 0;
        font-size: var(--hca-text-lg);
        color: var(--hca-text);
      }
      p {
        margin: 0;
        max-width: 420px;
        line-height: 1.5;
        font-size: var(--hca-text-sm);
      }
    `,
  ];

  @property() icon: IconName = "chat";
  @property() heading = "";

  render() {
    return html`
      <hca-icon name=${this.icon}></hca-icon>
      <h3>${this.heading}</h3>
      <p><slot></slot></p>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-empty-state": HcaEmptyState;
  }
}
