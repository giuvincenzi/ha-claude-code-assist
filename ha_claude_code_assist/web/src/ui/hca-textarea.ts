import { LitElement, css, html, nothing } from "lit";
import { customElement, property } from "lit/decorators.js";

import { base, controls, field } from "./styles";

/**
 * A multi-line field with its label, hint and error; `code` for JSON and similar (monospace,
 * no spellcheck). `value` follows what is typed; the native `input` event bubbles out.
 */
@customElement("hca-textarea")
export class HcaTextarea extends LitElement {
  static styles = [
    base,
    controls,
    field,
    css`
      textarea {
        resize: vertical;
        line-height: 1.45;
      }
      :host([code]) textarea {
        font-family: var(--hca-font-mono);
        font-size: var(--hca-text-sm);
      }
    `,
  ];

  @property() label = "";
  @property() hint = "";
  @property() error = "";
  @property() value = "";
  @property() placeholder = "";
  @property({ type: Number }) rows = 4;
  @property({ type: Boolean, reflect: true }) code = false;

  render() {
    return html`
      <div class="field">
        ${this.label ? html`<label for="control">${this.label}</label>` : nothing}
        <textarea
          id="control"
          rows=${this.rows}
          .value=${this.value}
          placeholder=${this.placeholder}
          spellcheck=${this.code ? "false" : "true"}
          aria-label=${this.label ? nothing : this.placeholder}
          aria-invalid=${this.error ? "true" : "false"}
          @input=${(e: Event) => (this.value = (e.target as HTMLTextAreaElement).value)}
        ></textarea>
        ${this.error ? html`<div class="error">${this.error}</div>` : nothing}
        ${this.hint ? html`<div class="hint">${this.hint}</div>` : nothing}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-textarea": HcaTextarea;
  }
}
