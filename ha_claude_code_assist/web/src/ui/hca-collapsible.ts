import { LitElement, css, html } from "lit";
import { customElement, property } from "lit/decorators.js";

import "./hca-icon";
import { base } from "./styles";

/** A summary line that opens to show its content: a native details element. */
@customElement("hca-collapsible")
export class HcaCollapsible extends LitElement {
  static styles = [
    base,
    css`
      :host {
        display: block;
      }
      summary {
        display: flex;
        align-items: center;
        gap: var(--hca-space-2);
        list-style: none;
        cursor: pointer;
        border-radius: var(--hca-radius-sm);
        --hca-icon-size: 14px;
      }
      summary::-webkit-details-marker {
        display: none;
      }
      .arrow {
        transition: transform 0.15s;
        color: var(--hca-text-muted);
      }
      details[open] .arrow {
        transform: rotate(90deg);
      }
      .content {
        padding: var(--hca-space-2) 0 0 22px;
      }
    `,
  ];

  @property({ type: Boolean }) open = false;

  render() {
    return html`
      <details ?open=${this.open} @toggle=${(e: Event) => (this.open = (e.target as HTMLDetailsElement).open)}>
        <summary><hca-icon class="arrow" name="chevron-right"></hca-icon><slot name="summary"></slot></summary>
        <div class="content"><slot></slot></div>
      </details>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-collapsible": HcaCollapsible;
  }
}
