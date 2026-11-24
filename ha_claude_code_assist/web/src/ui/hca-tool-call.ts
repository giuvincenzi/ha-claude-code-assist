import { LitElement, css, html } from "lit";
import { customElement, property } from "lit/decorators.js";

import "./hca-detail";
import "./hca-icon";
import "./hca-spinner";
import { base } from "./styles";

/**
 * One tool the assistant used: its name and state on a detail line, so it does not read as part
 * of the answer; what it sent and received opens below.
 */
@customElement("hca-tool-call")
export class HcaToolCall extends LitElement {
  static styles = [
    base,
    css`
      :host {
        display: block;
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
      running: html`<hca-spinner slot="end"></hca-spinner>`,
      ok: html`<hca-icon slot="end" class="ok" name="check"></hca-icon>`,
      failed: html`<hca-icon slot="end" class="failed" name="alert"></hca-icon>`,
    }[this.status];
    return html`<hca-detail icon="tool" label=${this.label}>${state}<slot></slot></hca-detail>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-tool-call": HcaToolCall;
  }
}
