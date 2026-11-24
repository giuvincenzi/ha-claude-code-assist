import { LitElement, css, html } from "lit";
import { customElement, property } from "lit/decorators.js";

import { base } from "./styles";

export interface Segment {
  value: string;
  label: string;
}

/**
 * A choice among a few options, side by side: native radio buttons, so the arrow keys move
 * between them. Fires `hca-change` with `detail.value` when another option is chosen.
 */
@customElement("hca-segmented")
export class HcaSegmented extends LitElement {
  static styles = [
    base,
    css`
      :host {
        display: inline-flex;
      }
      .group {
        display: inline-flex;
        gap: 2px;
        padding: 2px;
        border: 1px solid var(--hca-border-strong);
        border-radius: var(--hca-radius-sm);
        background: var(--hca-surface-muted);
      }
      label {
        position: relative;
        padding: var(--hca-space-1) var(--hca-space-3);
        border-radius: calc(var(--hca-radius-sm) - 2px);
        font-size: var(--hca-text-sm);
        font-weight: 600;
        color: var(--hca-text-muted);
        cursor: pointer;
        transition: background 0.15s, color 0.15s;
      }
      label:hover {
        color: var(--hca-text);
      }
      label:has(input:checked) {
        background: var(--hca-surface);
        color: var(--hca-text);
        box-shadow: var(--hca-shadow);
      }
      label:has(input:focus-visible) {
        box-shadow: var(--hca-focus);
      }
      input {
        position: absolute;
        opacity: 0;
        pointer-events: none;
      }
    `,
  ];

  @property({ attribute: false }) options: Segment[] = [];
  @property() value = "";
  /** The accessible name of the whole choice. */
  @property() label = "";

  private choose(value: string): void {
    this.value = value;
    this.dispatchEvent(new CustomEvent("hca-change", { detail: { value }, bubbles: true, composed: true }));
  }

  render() {
    return html`
      <div class="group" role="radiogroup" aria-label=${this.label}>
        ${this.options.map((option) => html`
          <label>
            <input type="radio" name="segment" .checked=${option.value === this.value}
              @change=${() => this.choose(option.value)}>${option.label}
          </label>
        `)}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-segmented": HcaSegmented;
  }
}
