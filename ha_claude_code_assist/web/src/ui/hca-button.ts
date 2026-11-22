import { LitElement, css, html, nothing } from "lit";
import { customElement, property } from "lit/decorators.js";

import "./hca-icon";
import type { IconName } from "./hca-icon";
import "./hca-spinner";
import { base } from "./styles";

/** A button: primary for the main action of a page, secondary, ghost, or danger. */
@customElement("hca-button")
export class HcaButton extends LitElement {
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
        gap: var(--hca-space-2);
        width: 100%;
        min-height: 36px;
        padding: 0 var(--hca-space-4);
        font: inherit;
        font-size: var(--hca-text-md);
        font-weight: 600;
        border-radius: var(--hca-radius-sm);
        border: 1px solid transparent;
        cursor: pointer;
        transition: background 0.15s, border-color 0.15s, color 0.15s;
        --hca-icon-size: 16px;
      }
      /* Centres the text on its capital letters, so it lines up with the icon (no effect where
         the browser does not support text-box). */
      .label {
        text-box: trim-both cap alphabetic;
      }
      button:disabled {
        opacity: 0.55;
        cursor: not-allowed;
      }
      :host([size="sm"]) button {
        min-height: 30px;
        padding: 0 var(--hca-space-3);
        font-size: var(--hca-text-sm);
      }
      .primary {
        background: var(--hca-accent);
        color: var(--hca-on-accent);
      }
      .primary:not(:disabled):hover {
        background: var(--hca-accent-hover);
      }
      .secondary {
        background: var(--hca-surface);
        border-color: var(--hca-border-strong);
        color: var(--hca-text);
      }
      .secondary:not(:disabled):hover {
        background: var(--hca-surface-muted);
      }
      .ghost {
        background: transparent;
        color: var(--hca-text-muted);
      }
      .ghost:not(:disabled):hover {
        background: var(--hca-surface-muted);
        color: var(--hca-text);
      }
      .danger {
        background: transparent;
        border-color: var(--hca-border-strong);
        color: var(--hca-error);
      }
      .danger:not(:disabled):hover {
        background: var(--hca-error-soft);
      }
    `,
  ];

  @property({ reflect: true }) variant: "primary" | "secondary" | "ghost" | "danger" = "secondary";
  @property({ reflect: true }) size: "sm" | "md" = "md";
  @property() icon?: IconName;
  @property({ type: Boolean }) disabled = false;
  @property({ type: Boolean }) loading = false;

  render() {
    return html`
      <button class=${this.variant} ?disabled=${this.disabled || this.loading}>
        ${this.loading
          ? html`<hca-spinner></hca-spinner>`
          : this.icon
            ? html`<hca-icon name=${this.icon}></hca-icon>`
            : nothing}
        <span class="label"><slot></slot></span>
      </button>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-button": HcaButton;
  }
}
