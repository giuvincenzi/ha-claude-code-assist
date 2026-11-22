import { LitElement, css, html } from "lit";
import { customElement, property } from "lit/decorators.js";

import { base } from "./styles";

export interface Property {
  label: string;
  value: string;
  /** Shown on hover, for the exact figure behind a rounded one. */
  hint?: string;
}

/** Facts about one thing, one per row: the label on the left, its value on the right. */
@customElement("hca-property-list")
export class HcaPropertyList extends LitElement {
  static styles = [
    base,
    css`
      dl {
        display: grid;
        grid-template-columns: max-content minmax(0, 1fr);
        margin: 0;
        font-size: var(--hca-text-md);
      }
      dt,
      dd {
        padding: var(--hca-space-2) 0;
        border-bottom: 1px solid var(--hca-border);
      }
      dt {
        padding-right: var(--hca-space-4);
        color: var(--hca-text-muted);
      }
      dd {
        margin: 0;
        text-align: right;
        overflow-wrap: anywhere;
      }
      dt:nth-last-of-type(1),
      dd:nth-last-of-type(1) {
        border-bottom: none;
      }
    `,
  ];

  @property({ attribute: false }) items: Property[] = [];

  render() {
    return html`<dl>
      ${this.items.map((item) => html`<dt>${item.label}</dt><dd title=${item.hint ?? item.value}>${item.value}</dd>`)}
    </dl>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-property-list": HcaPropertyList;
  }
}
