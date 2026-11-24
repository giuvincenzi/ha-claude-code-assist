import { LitElement, css, html } from "lit";
import { customElement, property } from "lit/decorators.js";

import "./hca-collapsible";
import "./hca-icon";
import type { IconName } from "./hca-icon";
import { base } from "./styles";

/**
 * Something that comes with a message without being part of it, such as a tool the assistant
 * used: an icon and a label on one small grey line, with more after the label (slot "end"); what
 * it holds opens below.
 */
@customElement("hca-detail")
export class HcaDetail extends LitElement {
  static styles = [
    base,
    css`
      :host {
        display: block;
        margin: var(--hca-space-1) 0;
        font-size: var(--hca-text-xs);
        color: var(--hca-text-muted);
        --hca-icon-size: 12px;
      }
      /* The collapsible sets its own text colour: the line stays grey, darker on hover. */
      hca-collapsible {
        color: inherit;
      }
      .summary:hover {
        color: var(--hca-text);
      }
      .summary {
        display: inline-flex;
        align-items: center;
        gap: var(--hca-space-2);
      }
    `,
  ];

  @property() icon: IconName = "info";
  @property() label = "";

  render() {
    return html`
      <hca-collapsible>
        <span slot="summary" class="summary"><hca-icon name=${this.icon}></hca-icon>${this.label}<slot name="end"></slot></span>
        <slot></slot>
      </hca-collapsible>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-detail": HcaDetail;
  }
}
