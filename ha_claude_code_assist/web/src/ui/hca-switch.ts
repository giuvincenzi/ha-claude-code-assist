import { LitElement, css, html, nothing } from "lit";
import { customElement, property } from "lit/decorators.js";

import { base, field } from "./styles";

/**
 * An on/off switch: a native checkbox with the switch role, its label beside it and the hint
 * below. Fires `change` (bubbling) when toggled.
 */
@customElement("hca-switch")
export class HcaSwitch extends LitElement {
  static styles = [
    base,
    field,
    css`
      .row {
        display: flex;
        align-items: center;
        gap: var(--hca-space-3);
      }
      input {
        appearance: none;
        position: relative;
        flex-shrink: 0;
        width: 38px;
        height: 22px;
        margin: 0;
        border-radius: var(--hca-radius-full);
        background: var(--hca-border-strong);
        cursor: pointer;
        transition: background 0.15s;
      }
      input::after {
        content: "";
        position: absolute;
        top: 3px;
        left: 3px;
        width: 16px;
        height: 16px;
        border-radius: 50%;
        background: #fff;
        transition: transform 0.15s;
      }
      input:checked {
        background: var(--hca-accent);
      }
      input:checked::after {
        transform: translateX(16px);
      }
      label {
        cursor: pointer;
      }
      @media (prefers-reduced-motion: reduce) {
        input,
        input::after {
          transition: none;
        }
      }
    `,
  ];

  @property() label = "";
  @property() hint = "";
  @property({ type: Boolean }) checked = false;

  private onChange(event: Event): void {
    this.checked = (event.target as HTMLInputElement).checked;
    this.dispatchEvent(new Event("change", { bubbles: true, composed: true }));
  }

  render() {
    return html`
      <div class="field">
        <div class="row">
          <input id="control" type="checkbox" role="switch" .checked=${this.checked} @change=${this.onChange} />
          <label for="control">${this.label}</label>
        </div>
        ${this.hint ? html`<div class="hint">${this.hint}</div>` : nothing}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-switch": HcaSwitch;
  }
}
