import { LitElement, css, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";

import { base, controls, field } from "./styles";

/**
 * A text, password or number field with its label, hint and error. Slot "status": a short state
 * shown next to the label. Slot "hint": a hint with formatting (it replaces `hint`). `value` follows what is
 * typed; the native `input` event bubbles out of the component.
 */
@customElement("hca-input")
export class HcaInput extends LitElement {
  static styles = [
    base,
    controls,
    field,
    css`
      .label-row {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: var(--hca-space-1) var(--hca-space-2);
      }
    `,
  ];

  @property() label = "";
  @property() hint = "";
  @property() error = "";
  @property() value = "";
  @property() type: "text" | "password" | "number" = "text";
  @property() placeholder = "";
  @property() autocomplete = "off";
  @property({ type: Number }) min?: number;
  @property({ type: Number }) max?: number;
  @property({ type: Number }) maxlength?: number;
  @property({ type: Boolean }) disabled = false;
  @state() private slottedHint = false;

  private onHintSlot(event: Event): void {
    this.slottedHint = (event.target as HTMLSlotElement).assignedNodes().length > 0;
  }

  /** Moves the focus into the field. */
  override focus(): void {
    this.renderRoot.querySelector("input")?.focus();
  }

  render() {
    return html`
      <div class="field">
        ${this.label
          ? html`<div class="label-row"><label for="control">${this.label}</label><slot name="status"></slot></div>`
          : nothing}
        <input
          id="control"
          type=${this.type}
          .value=${this.value}
          placeholder=${this.placeholder}
          autocomplete=${this.autocomplete}
          min=${this.min ?? nothing}
          max=${this.max ?? nothing}
          maxlength=${this.maxlength ?? nothing}
          ?disabled=${this.disabled}
          aria-label=${this.label ? nothing : this.placeholder}
          aria-invalid=${this.error ? "true" : "false"}
          @input=${(e: Event) => (this.value = (e.target as HTMLInputElement).value)}
        />
        ${this.error ? html`<div class="error">${this.error}</div>` : nothing}
        <div class="hint" ?hidden=${!this.hint && !this.slottedHint}>
          <slot name="hint" @slotchange=${this.onHintSlot}>${this.hint}</slot>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-input": HcaInput;
  }
}
