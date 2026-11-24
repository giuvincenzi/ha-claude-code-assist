import { LitElement, css, html } from "lit";
import { customElement, property } from "lit/decorators.js";

import "./hca-icon";
import type { IconName } from "./hca-icon";
import { base } from "./styles";

export interface Tab {
  id: string;
  label: string;
  icon?: IconName;
  /** Marks the tab with a dot; the text says why (its tooltip, and read with its name). */
  mark?: string;
}

/**
 * A row of tabs (WAI-ARIA tabs pattern: one tab in the Tab order, arrow keys, Home and End move
 * between tabs). Fires `hca-select` with `detail.id` when a tab is chosen.
 */
@customElement("hca-tabs")
export class HcaTabs extends LitElement {
  static styles = [
    base,
    css`
      [role="tablist"] {
        display: flex;
        gap: var(--hca-space-1);
        overflow-x: auto;
        scrollbar-width: none;
      }
      button {
        display: inline-flex;
        align-items: center;
        gap: var(--hca-space-2);
        padding: var(--hca-space-2) var(--hca-space-3);
        border: none;
        border-radius: var(--hca-radius-sm);
        background: transparent;
        color: var(--hca-text-muted);
        font: inherit;
        font-weight: 600;
        white-space: nowrap;
        cursor: pointer;
        --hca-icon-size: 16px;
      }
      button:hover {
        background: var(--hca-surface-muted);
        color: var(--hca-text);
      }
      button[aria-selected="true"] {
        background: var(--hca-accent-soft);
        color: var(--hca-accent);
      }
      .mark {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: var(--hca-accent);
      }
      /* Narrow screens: icons only; the name stays as tooltip and accessible name. */
      @media (max-width: 600px) {
        [role="tablist"] {
          justify-content: space-between;
        }
        .has-icon .label {
          display: none;
        }
      }
    `,
  ];

  @property({ attribute: false }) tabs: Tab[] = [];
  @property() selected = "";
  @property() label = "";

  private select(id: string, focus: boolean): void {
    this.selected = id;
    this.dispatchEvent(new CustomEvent("hca-select", { detail: { id }, bubbles: true, composed: true }));
    if (focus) this.updateComplete.then(() => this.renderRoot.querySelector<HTMLElement>(`[data-id="${id}"]`)?.focus());
  }

  private onKeydown(event: KeyboardEvent): void {
    const index = this.tabs.findIndex((t) => t.id === this.selected);
    const last = this.tabs.length - 1;
    const next = { ArrowRight: index + 1, ArrowLeft: index - 1, Home: 0, End: last }[event.key];
    if (next === undefined) return;
    event.preventDefault();
    this.select(this.tabs[(next + this.tabs.length) % this.tabs.length].id, true);
  }

  render() {
    return html`
      <div role="tablist" aria-label=${this.label} @keydown=${this.onKeydown}>
        ${this.tabs.map((tab) => html`
          <button role="tab" data-id=${tab.id} class=${tab.icon ? "has-icon" : ""}
            title=${tab.mark ? `${tab.label}. ${tab.mark}` : tab.label}
            aria-label=${tab.mark ? `${tab.label}. ${tab.mark}` : tab.label}
            aria-selected=${tab.id === this.selected ? "true" : "false"}
            tabindex=${tab.id === this.selected ? 0 : -1} @click=${() => this.select(tab.id, false)}>
            ${tab.icon ? html`<hca-icon name=${tab.icon}></hca-icon>` : ""}<span class="label">${tab.label}</span>
            ${tab.mark ? html`<span class="mark"></span>` : ""}
          </button>
        `)}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-tabs": HcaTabs;
  }
}
