import { LitElement, css, html, nothing } from "lit";
import { customElement, property } from "lit/decorators.js";

import type { Connection } from "../lib/connection";
import "../ui/hca-banner";

/**
 * Floats at the top of the content, under the header, while the panel is not connected to the
 * app (it reconnects on its own). It never takes space in the page, so nothing moves when it
 * appears. Its parent must be positioned.
 */
@customElement("hca-connection-banner")
export class HcaConnectionBanner extends LitElement {
  static styles = css`
    :host {
      position: absolute;
      left: 50%;
      top: var(--hca-space-3);
      z-index: 10;
      transform: translateX(-50%);
      width: max-content;
      max-width: calc(100vw - 2 * var(--hca-space-4));
      box-shadow: var(--hca-shadow);
    }
    :host([state="open"]) {
      display: none;
    }
  `;

  @property({ reflect: true }) state: Connection["state"] = "connecting";

  render() {
    if (this.state === "open") return nothing;
    return html`
      <hca-banner tone=${this.state === "closed" ? "warn" : "info"}>
        ${this.state === "closed" ? "Connection to the app lost: reconnecting…" : "Connecting to the app…"}
      </hca-banner>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-connection-banner": HcaConnectionBanner;
  }
}
