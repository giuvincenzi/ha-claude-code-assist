import { LitElement, css, html, nothing } from "lit";
import { customElement, property } from "lit/decorators.js";

import { base } from "./styles";

/**
 * A card with a heading, an optional description and actions (slot "actions", top right),
 * then its content. The building block of every page.
 */
@customElement("hca-section")
export class HcaSection extends LitElement {
  static styles = [
    base,
    css`
      :host {
        display: block;
        background: var(--hca-surface);
        border: 1px solid var(--hca-border);
        border-radius: var(--hca-radius);
        box-shadow: var(--hca-shadow);
      }
      header {
        display: flex;
        flex-wrap: wrap;
        align-items: flex-start;
        gap: var(--hca-space-3);
        padding: var(--hca-space-4) var(--hca-space-5) 0;
      }
      .titles {
        flex: 1 1 240px;
        min-width: 0;
      }
      h2 {
        margin: 0;
        font-size: var(--hca-text-lg);
        font-weight: 650;
      }
      p {
        margin: var(--hca-space-1) 0 0;
        font-size: var(--hca-text-sm);
        line-height: 1.45;
        color: var(--hca-text-muted);
      }
      .content {
        display: grid;
        /* One column as wide as the section: without it the column grows to its widest content
           (a line that does not wrap) and the content leaves the section. */
        grid-template-columns: minmax(0, 1fr);
        gap: var(--hca-space-4);
        padding: var(--hca-space-4) var(--hca-space-5) var(--hca-space-5);
      }
    `,
  ];

  @property() heading = "";
  @property() description = "";

  render() {
    return html`
      ${this.heading
        ? html`<header>
            <div class="titles">
              <h2>${this.heading}</h2>
              ${this.description ? html`<p>${this.description}</p>` : nothing}
            </div>
            <slot name="actions"></slot>
          </header>`
        : nothing}
      <div class="content"><slot></slot></div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-section": HcaSection;
  }
}
