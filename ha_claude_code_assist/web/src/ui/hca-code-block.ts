import { LitElement, css, html } from "lit";
import { customElement, property } from "lit/decorators.js";

import { base } from "./styles";

/** Preformatted text (JSON, tool results), scrolling when long. */
@customElement("hca-code-block")
export class HcaCodeBlock extends LitElement {
  static styles = [
    base,
    css`
      pre {
        margin: var(--hca-space-1) 0;
        padding: var(--hca-space-2) var(--hca-space-3);
        max-height: 240px;
        overflow: auto;
        border-radius: var(--hca-radius-sm);
        background: var(--hca-surface-muted);
        color: var(--hca-text);
        font-family: var(--hca-font-mono);
        font-size: var(--hca-text-xs);
        white-space: pre-wrap;
        word-break: break-word;
      }
    `,
  ];

  @property() code = "";

  render() {
    return html`<pre>${this.code}</pre>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-code-block": HcaCodeBlock;
  }
}
