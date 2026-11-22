import { LitElement, css, html } from "lit";
import { customElement, property } from "lit/decorators.js";

import "./hca-icon";
import type { IconName } from "./hca-icon";
import { base } from "./styles";

/** A button with only an icon; `label` names it for screen readers and the tooltip. */
@customElement("hca-icon-button")
export class HcaIconButton extends LitElement {
  static styles = [
    base,
    css`
      :host {
        display: inline-flex;
      }
      button {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 36px;
        height: 36px;
        border: none;
        border-radius: var(--hca-radius-sm);
        background: transparent;
        color: var(--hca-text-muted);
        cursor: pointer;
        transition: background 0.15s, color 0.15s;
      }
      button:not(:disabled):hover {
        background: var(--hca-surface-muted);
        color: var(--hca-text);
      }
      :host([variant="primary"]) button {
        background: var(--hca-accent);
        color: var(--hca-on-accent);
        border-radius: var(--hca-radius-full);
      }
      :host([variant="primary"]) button:not(:disabled):hover {
        background: var(--hca-accent-hover);
      }
      button:disabled {
        opacity: 0.45;
        cursor: not-allowed;
      }
    `,
  ];

  @property() icon: IconName = "chat";
  @property() label = "";
  @property({ reflect: true }) variant: "ghost" | "primary" = "ghost";
  @property({ type: Boolean }) disabled = false;

  render() {
    return html`
      <button aria-label=${this.label} title=${this.label} ?disabled=${this.disabled}>
        <hca-icon name=${this.icon}></hca-icon>
      </button>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-icon-button": HcaIconButton;
  }
}
