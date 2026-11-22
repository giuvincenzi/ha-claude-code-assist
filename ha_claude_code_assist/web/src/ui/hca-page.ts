import { LitElement, css, html } from "lit";
import { customElement, property } from "lit/decorators.js";

/** The centred column every page lives in: default width, or narrow (the chat). */
@customElement("hca-page")
export class HcaPage extends LitElement {
  static styles = css`
    :host {
      display: block;
      width: 100%;
      max-width: var(--hca-page-width);
      margin: 0 auto;
      padding: var(--hca-space-5) var(--hca-space-4);
      box-sizing: border-box;
    }
    :host([width="narrow"]) {
      max-width: var(--hca-page-width-narrow);
    }
    ::slotted(*:not(:last-child)) {
      margin-bottom: var(--hca-space-4);
    }
  `;

  @property({ reflect: true }) width: "default" | "narrow" = "default";

  render() {
    return html`<slot></slot>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-page": HcaPage;
  }
}
