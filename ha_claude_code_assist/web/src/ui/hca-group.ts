import { LitElement, css, html, nothing } from "lit";
import { customElement, property } from "lit/decorators.js";

import { base } from "./styles";

/**
 * Content under a small label in capitals, which names a group inside a section; `divided` draws
 * a line above it, when it follows other content.
 */
@customElement("hca-group")
export class HcaGroup extends LitElement {
  static styles = [
    base,
    css`
      :host {
        display: block;
      }
      :host([divided]) {
        margin-top: var(--hca-space-4);
        padding-top: var(--hca-space-4);
        border-top: 1px solid var(--hca-border);
      }
      .label {
        margin: 0 0 var(--hca-space-2);
        font-size: var(--hca-text-xs);
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--hca-text-muted);
      }
    `,
  ];

  @property() label = "";
  @property({ type: Boolean, reflect: true }) divided = false;

  render() {
    return html`${this.label ? html`<div class="label">${this.label}</div>` : nothing}<slot></slot>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-group": HcaGroup;
  }
}
