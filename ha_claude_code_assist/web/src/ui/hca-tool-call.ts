import { LitElement, css, html } from "lit";
import { customElement, property } from "lit/decorators.js";

import "./hca-collapsible";
import "./hca-icon";
import "./hca-spinner";
import { base } from "./styles";

/**
 * One tool the assistant used: its name and state on one small grey line, so it does not read as
 * part of the answer; the details open below.
 */
@customElement("hca-tool-call")
export class HcaToolCall extends LitElement {
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
      .ok {
        color: var(--hca-ok);
      }
      .failed {
        color: var(--hca-error);
      }
    `,
  ];

  @property() label = "";
  @property({ reflect: true }) status: "running" | "ok" | "failed" = "running";

  render() {
    const state = {
      running: html`<hca-spinner></hca-spinner>`,
      ok: html`<hca-icon class="ok" name="check"></hca-icon>`,
      failed: html`<hca-icon class="failed" name="alert"></hca-icon>`,
    }[this.status];
    return html`
      <hca-collapsible>
        <span slot="summary" class="summary"><hca-icon name="tool"></hca-icon>${this.label}${state}</span>
        <slot></slot>
      </hca-collapsible>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-tool-call": HcaToolCall;
  }
}
