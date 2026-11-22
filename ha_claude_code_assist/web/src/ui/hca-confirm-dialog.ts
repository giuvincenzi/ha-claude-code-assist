import { LitElement, css, html } from "lit";
import { customElement, query, state } from "lit/decorators.js";

import "./hca-button";
import { base } from "./styles";

export interface ConfirmOptions {
  heading: string;
  message: string;
  confirmLabel: string;
  danger?: boolean;
}

/**
 * A modal question with Cancel and a confirm button: a native dialog (focus kept inside, Esc
 * cancels). `ask()` resolves to true when confirmed.
 */
@customElement("hca-confirm-dialog")
export class HcaConfirmDialog extends LitElement {
  static styles = [
    base,
    css`
      dialog {
        width: min(440px, calc(100vw - 32px));
        padding: var(--hca-space-5);
        border: 1px solid var(--hca-border);
        border-radius: var(--hca-radius);
        background: var(--hca-surface);
        color: var(--hca-text);
        box-shadow: 0 10px 30px rgb(0 0 0 / 0.25);
      }
      dialog::backdrop {
        background: rgb(0 0 0 / 0.4);
      }
      h2 {
        margin: 0 0 var(--hca-space-2);
        font-size: var(--hca-text-lg);
      }
      p {
        margin: 0 0 var(--hca-space-5);
        line-height: 1.5;
        color: var(--hca-text-muted);
        white-space: pre-wrap;
      }
      .actions {
        display: flex;
        justify-content: flex-end;
        gap: var(--hca-space-2);
      }
    `,
  ];

  @state() private options: ConfirmOptions = { heading: "", message: "", confirmLabel: "OK" };
  @query("dialog") private dialog!: HTMLDialogElement;
  private resolve?: (confirmed: boolean) => void;

  async ask(options: ConfirmOptions): Promise<boolean> {
    this.options = options;
    await this.updateComplete;
    this.dialog.showModal();
    return new Promise((resolve) => (this.resolve = resolve));
  }

  private close(confirmed: boolean): void {
    this.dialog.close();
    this.resolve?.(confirmed);
    this.resolve = undefined;
  }

  render() {
    const o = this.options;
    return html`
      <dialog @cancel=${() => this.close(false)} aria-labelledby="heading">
        <h2 id="heading">${o.heading}</h2>
        <p>${o.message}</p>
        <div class="actions">
          <hca-button @click=${() => this.close(false)}>Cancel</hca-button>
          <hca-button variant=${o.danger ? "danger" : "primary"} @click=${() => this.close(true)}>${o.confirmLabel}</hca-button>
        </div>
      </dialog>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-confirm-dialog": HcaConfirmDialog;
  }
}
