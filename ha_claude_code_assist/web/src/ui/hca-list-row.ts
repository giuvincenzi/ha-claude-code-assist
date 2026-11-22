import { LitElement, css, html, nothing } from "lit";
import { customElement, property } from "lit/decorators.js";

import { base } from "./styles";

/**
 * One row of a list: a heading, a grey line under it, and something on the right (slot "end").
 *
 * A `selectable` row is one button, end slot included: hover and selection cover the whole row,
 * and it fires `hca-select`. Its end slot must hold nothing interactive (a badge, not a button).
 * A plain row can hold buttons in its end slot.
 */
@customElement("hca-list-row")
export class HcaListRow extends LitElement {
  static styles = [
    base,
    css`
      :host {
        display: block;
      }
      .row {
        display: flex;
        align-items: center;
        gap: var(--hca-space-3);
        width: 100%;
        padding: var(--hca-space-2) var(--hca-space-3);
        border: none;
        border-radius: var(--hca-radius-sm);
        background: transparent;
        color: inherit;
        font: inherit;
        text-align: left;
      }
      :host(:not([selectable])) .row {
        padding: var(--hca-space-3) var(--hca-space-2);
        border-bottom: 1px solid var(--hca-border);
        border-radius: 0;
      }
      :host(:not([selectable]):last-of-type) .row {
        border-bottom: none;
      }
      button.row {
        cursor: pointer;
        transition: background 0.12s;
      }
      button.row:hover {
        background: var(--hca-surface-muted);
      }
      :host([selected]) button.row,
      :host([selected]) button.row:hover {
        background: var(--hca-accent-soft);
      }
      .text {
        flex: 1;
        min-width: 0;
      }
      .heading {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        line-height: 1.4;
      }
      :host([selected]) .heading {
        color: var(--hca-accent);
        font-weight: 600;
      }
      .detail {
        margin-top: 2px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        font-size: var(--hca-text-xs);
        color: var(--hca-text-muted);
      }
      .end {
        display: flex;
        align-items: center;
        gap: var(--hca-space-1);
        flex-shrink: 0;
      }
    `,
  ];

  @property() heading = "";
  @property() detail = "";
  @property({ type: Boolean, reflect: true }) selectable = false;
  @property({ type: Boolean, reflect: true }) selected = false;

  render() {
    const content = html`
      <div class="text">
        <div class="heading">${this.heading}<slot name="heading"></slot></div>
        ${this.detail ? html`<div class="detail">${this.detail}</div>` : nothing}
      </div>
      <div class="end"><slot name="end"></slot></div>
    `;
    return this.selectable
      ? html`<button class="row" aria-current=${this.selected ? "true" : "false"}
          @click=${() => this.dispatchEvent(new CustomEvent("hca-select", { bubbles: true, composed: true }))}>${content}</button>`
      : html`<div class="row">${content}</div>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-list-row": HcaListRow;
  }
}
