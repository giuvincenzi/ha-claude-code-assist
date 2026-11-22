import { LitElement, css, html } from "lit";
import { customElement, property } from "lit/decorators.js";

import { base } from "./styles";

/**
 * A page with a sidebar on the right (slot "sidebar", with its own heading) and the main content
 * on the left; each scrolls on its own. On narrow screens the sidebar goes on top.
 */
@customElement("hca-sidebar-layout")
export class HcaSidebarLayout extends LitElement {
  static styles = [
    base,
    css`
      :host {
        display: grid;
        grid-template-columns: minmax(0, 1fr) 340px;
        height: 100%;
      }
      main {
        min-width: 0;
        overflow-y: auto;
      }
      aside {
        display: flex;
        flex-direction: column;
        min-height: 0;
        border-left: 1px solid var(--hca-border);
        background: var(--hca-surface);
      }
      h2 {
        margin: 0;
        padding: var(--hca-space-4) var(--hca-space-4) var(--hca-space-2);
        font-size: var(--hca-text-sm);
        font-weight: 650;
        color: var(--hca-text-muted);
        text-transform: uppercase;
        letter-spacing: 0.04em;
      }
      .list {
        flex: 1;
        min-height: 0;
        overflow-y: auto;
        padding: 0 var(--hca-space-2) var(--hca-space-3);
      }
      @media (max-width: 800px) {
        :host {
          grid-template-columns: minmax(0, 1fr);
          grid-template-rows: minmax(0, 40%) minmax(0, 1fr);
        }
        aside {
          grid-row: 1;
          border-left: none;
          border-bottom: 1px solid var(--hca-border);
        }
      }
    `,
  ];

  @property() heading = "";

  render() {
    return html`
      <main><slot></slot></main>
      <aside aria-label=${this.heading}>
        <h2>${this.heading}</h2>
        <div class="list"><slot name="sidebar"></slot></div>
      </aside>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-sidebar-layout": HcaSidebarLayout;
  }
}
