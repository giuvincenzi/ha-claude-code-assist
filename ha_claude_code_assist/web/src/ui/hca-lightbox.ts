import { LitElement, css, html, nothing } from "lit";
import { customElement, query, state } from "lit/decorators.js";

import "./hca-icon";
import { base } from "./styles";

interface Shown {
  src: string;
  name: string;
  download: string;
}

/**
 * A picture opened over the page: it grows into the middle, its name under it, Close and
 * Download at its top right corner. A native modal dialog: Escape, a click outside or Close
 * shut it, and the focus comes back where it was.
 */
@customElement("hca-lightbox")
export class HcaLightbox extends LitElement {
  static styles = [
    base,
    css`
      dialog {
        width: 100%;
        max-width: none;
        height: 100%;
        max-height: none;
        margin: 0;
        padding: var(--hca-space-6) var(--hca-space-4);
        border: none;
        background: var(--hca-backdrop);
        color: var(--hca-on-backdrop);
      }
      dialog[open] {
        display: grid;
        place-items: center;
        animation: fade 0.18s ease-out;
      }
      dialog::backdrop {
        background: transparent;
      }
      figure {
        display: grid;
        justify-items: center;
        gap: var(--hca-space-3);
        margin: 0;
        animation: grow 0.2s ease-out;
      }
      .frame {
        position: relative;
      }
      img {
        display: block;
        max-width: min(90vw, 1400px);
        max-height: 80vh;
        border-radius: var(--hca-radius);
        box-shadow: var(--hca-shadow);
      }
      figcaption {
        max-width: 90vw;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        font-size: var(--hca-text-sm);
      }
      /* Just outside the picture's top right corner, one above the other. */
      .actions {
        position: absolute;
        top: 0;
        left: 100%;
        display: grid;
        gap: var(--hca-space-1);
        padding-left: var(--hca-space-2);
      }
      .actions button,
      .actions a {
        display: grid;
        place-items: center;
        width: 32px;
        height: 32px;
        padding: 0;
        border: none;
        border-radius: var(--hca-radius-full);
        background: transparent;
        color: var(--hca-on-backdrop);
        cursor: pointer;
        --hca-icon-size: 20px;
      }
      .actions button:hover,
      .actions a:hover {
        background: var(--hca-backdrop);
      }
      /* Little room on the sides: the buttons go inside the corner. */
      @media (max-width: 600px) {
        .actions {
          left: auto;
          right: var(--hca-space-2);
          top: var(--hca-space-2);
          padding-left: 0;
        }
        .actions button,
        .actions a {
          background: var(--hca-backdrop);
        }
      }
      @keyframes fade {
        from {
          background: transparent;
        }
      }
      @keyframes grow {
        from {
          opacity: 0;
          transform: scale(0.92);
        }
      }
      @media (prefers-reduced-motion: reduce) {
        dialog[open],
        figure {
          animation: none;
        }
      }
    `,
  ];

  @state() private shown: Shown | null = null;
  @query("dialog") private dialog!: HTMLDialogElement;

  /** Opens a picture; `download` is the address its Download button saves. */
  async show(src: string, name: string, download: string): Promise<void> {
    this.shown = { src, name, download };
    await this.updateComplete;
    if (!this.dialog.open) this.dialog.showModal();
  }

  private close(): void {
    this.dialog.close();
  }

  render() {
    const s = this.shown;
    return html`
      <dialog aria-label=${s?.name ?? ""} @close=${() => (this.shown = null)}
        @click=${(e: MouseEvent) => e.target === this.dialog && this.close()}>
        ${s
          ? html`<figure>
              <div class="frame">
                <img src=${s.src} alt=${s.name}>
                <div class="actions">
                  <button type="button" aria-label="Close" title="Close" @click=${this.close}><hca-icon name="x"></hca-icon></button>
                  <a href=${s.download} download=${s.name} aria-label="Download" title="Download"><hca-icon name="download"></hca-icon></a>
                </div>
              </div>
              <figcaption>${s.name}</figcaption>
            </figure>`
          : nothing}
      </dialog>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-lightbox": HcaLightbox;
  }
}
