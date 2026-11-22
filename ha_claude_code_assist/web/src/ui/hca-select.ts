import { LitElement, css, html, nothing, type PropertyValues } from "lit";
import { customElement, property, query } from "lit/decorators.js";

import { base, controls, field } from "./styles";

export interface SelectOption {
  value: string;
  label: string;
  /** Shown after the label in the open list only ("Haiku - the fastest …"). */
  description?: string;
}

/** Where the browser lets a select show other content when closed than in its list. */
const CUSTOMIZABLE = typeof CSS !== "undefined" && CSS.supports("appearance", "base-select");

/**
 * A native select with its label and hint. Fires `change` (bubbling) when the value changes.
 *
 * An option's description shows in the open list, after its label. Where the browser supports
 * the customizable select (`appearance: base-select` and `<selectedcontent>`), the closed select
 * shows the label only; elsewhere it shows the whole text, as a classic select does.
 *
 * The options are built with the DOM rather than the template: a parser without customizable
 * select support drops elements written inside `<option>` and `<select>`, the DOM keeps them.
 */
@customElement("hca-select")
export class HcaSelect extends LitElement {
  static styles = [
    base,
    controls,
    field,
    css`
      .description {
        color: var(--hca-text-muted);
      }
      @supports (appearance: base-select) {
        select,
        ::picker(select) {
          appearance: base-select;
        }
        select {
          display: flex;
          align-items: center;
          justify-content: space-between;
          cursor: pointer;
        }
        selectedcontent .description {
          display: none;
        }
        ::picker(select) {
          margin-top: var(--hca-space-1);
          padding: var(--hca-space-1);
          border: 1px solid var(--hca-border-strong);
          border-radius: var(--hca-radius-sm);
          background: var(--hca-surface);
          color: var(--hca-text);
          box-shadow: var(--hca-shadow);
        }
        option {
          padding: var(--hca-space-2) var(--hca-space-3);
          border-radius: var(--hca-radius-sm);
          cursor: pointer;
        }
        option:hover,
        option:focus-visible {
          background: var(--hca-surface-muted);
          box-shadow: none;
        }
        option:checked {
          font-weight: 600;
        }
        option::checkmark {
          color: var(--hca-accent);
        }
      }
    `,
  ];

  @property() label = "";
  @property() hint = "";
  @property() value = "";
  @property({ attribute: false }) options: SelectOption[] = [];
  @query("select") private select!: HTMLSelectElement;

  private onChange(event: Event): void {
    this.value = (event.target as HTMLSelectElement).value;
    this.dispatchEvent(new Event("change", { bubbles: true, composed: true }));
  }

  protected updated(changed: PropertyValues<this>): void {
    if (changed.has("options")) this.buildOptions();
    if (changed.has("options") || changed.has("value")) this.select.value = this.value;
  }

  private buildOptions(): void {
    const children: Node[] = [];
    if (CUSTOMIZABLE) {
      // The closed select shows a copy of the chosen option, here without its description.
      const button = document.createElement("button");
      button.append(document.createElement("selectedcontent"));
      children.push(button);
    }
    for (const o of this.options) {
      const option = document.createElement("option");
      option.value = o.value;
      const label = document.createElement("span");
      label.textContent = o.label;
      option.append(label);
      if (o.description) {
        const description = document.createElement("span");
        description.className = "description";
        description.textContent = ` - ${o.description}`;
        option.append(description);
      }
      children.push(option);
    }
    this.select.replaceChildren(...children);
  }

  render() {
    return html`
      <div class="field">
        ${this.label ? html`<label for="control">${this.label}</label>` : nothing}
        <select id="control" @change=${this.onChange}></select>
        ${this.hint ? html`<div class="hint">${this.hint}</div>` : nothing}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-select": HcaSelect;
  }
}
