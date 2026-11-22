import { LitElement, css, html } from "lit";
import { customElement } from "lit/decorators.js";

import { base } from "./styles";

/**
 * Two halves side by side (slots "start" and "end") with a vertical line between them; one
 * above the other, with a horizontal line, when there is little room.
 */
@customElement("hca-split")
export class HcaSplit extends LitElement {
  static styles = [
    base,
    css`
      :host {
        display: block;
        container-type: inline-size;
      }
      .split {
        display: grid;
        grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      }
      .start {
        padding-right: var(--hca-space-5);
      }
      .end {
        padding-left: var(--hca-space-5);
        border-left: 1px solid var(--hca-border);
      }
      @container (max-width: 560px) {
        .split {
          grid-template-columns: minmax(0, 1fr);
        }
        .start {
          padding: 0 0 var(--hca-space-4);
        }
        .end {
          padding: var(--hca-space-4) 0 0;
          border-left: none;
          border-top: 1px solid var(--hca-border);
        }
      }
    `,
  ];

  render() {
    return html`<div class="split">
      <div class="start"><slot name="start"></slot></div>
      <div class="end"><slot name="end"></slot></div>
    </div>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-split": HcaSplit;
  }
}
