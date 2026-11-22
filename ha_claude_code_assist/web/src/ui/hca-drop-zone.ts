import { LitElement, css, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";

import "./hca-icon";
import { base } from "./styles";

/**
 * Lets files be dropped anywhere on the page while it is shown: dragging files over the window
 * covers it with a frame that says what can be dropped, and dropping fires `hca-drop` with
 * `detail.files`. When `disabled`, the frame says why instead (`reason`) and nothing is taken.
 * Files dropped on the page are never opened by the browser in its place.
 *
 * Only files coming from outside count: dragging a picture of the page carries its file too,
 * and that must not attach it again. A drag that starts in the page fires `dragstart` here,
 * one from the desktop does not.
 */
@customElement("hca-drop-zone")
export class HcaDropZone extends LitElement {
  static styles = [
    base,
    css`
      :host {
        display: contents;
      }
      .overlay {
        position: fixed;
        inset: 0;
        z-index: 20;
        display: grid;
        padding: var(--hca-space-3);
        background: var(--hca-backdrop);
        backdrop-filter: blur(3px);
        animation: fade 0.12s ease-out;
        pointer-events: none;
      }
      .frame {
        display: grid;
        place-content: center;
        justify-items: center;
        gap: var(--hca-space-2);
        border: 2px dashed var(--hca-accent);
        border-radius: var(--hca-radius-lg);
        color: var(--hca-on-backdrop);
        text-align: center;
        --hca-icon-size: 32px;
      }
      .disabled .frame {
        border-color: var(--hca-border-strong);
      }
      .icons {
        display: flex;
        gap: var(--hca-space-3);
        color: var(--hca-accent);
      }
      .heading {
        font-size: var(--hca-text-lg);
        font-weight: 650;
      }
      .message {
        font-size: var(--hca-text-sm);
        opacity: 0.85;
      }
      @keyframes fade {
        from {
          opacity: 0;
        }
      }
      @media (prefers-reduced-motion: reduce) {
        .overlay {
          animation: none;
        }
      }
    `,
  ];

  @property() heading = "Drop files here";
  @property() message = "";
  @property({ type: Boolean }) disabled = false;
  @property() reason = "";
  @state() private dragging = false;
  // Entering a child element fires dragenter before the parent's dragleave: counting them tells
  // when the files really left the window, so the frame does not flicker.
  private depth = 0;
  private draggingFromPage = false;

  connectedCallback(): void {
    super.connectedCallback();
    window.addEventListener("dragstart", this.onStart);
    window.addEventListener("dragend", this.onEnd);
    window.addEventListener("dragenter", this.onEnter);
    window.addEventListener("dragover", this.onOver);
    window.addEventListener("dragleave", this.onLeave);
    window.addEventListener("drop", this.onDrop);
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    window.removeEventListener("dragstart", this.onStart);
    window.removeEventListener("dragend", this.onEnd);
    window.removeEventListener("dragenter", this.onEnter);
    window.removeEventListener("dragover", this.onOver);
    window.removeEventListener("dragleave", this.onLeave);
    window.removeEventListener("drop", this.onDrop);
  }

  private carriesFiles(event: DragEvent): boolean {
    return !this.draggingFromPage && Boolean(event.dataTransfer?.types.includes("Files"));
  }

  private onStart = (): void => {
    this.draggingFromPage = true;
  };

  private onEnd = (): void => {
    this.draggingFromPage = false;
  };

  private onEnter = (event: DragEvent): void => {
    if (!this.carriesFiles(event)) return;
    event.preventDefault();
    this.depth++;
    this.dragging = true;
  };

  private onOver = (event: DragEvent): void => {
    if (!this.carriesFiles(event)) return;
    event.preventDefault();  // without it the browser would open the file instead of dropping it
    if (event.dataTransfer) event.dataTransfer.dropEffect = this.disabled ? "none" : "copy";
  };

  private onLeave = (event: DragEvent): void => {
    if (!this.carriesFiles(event)) return;
    this.depth = Math.max(0, this.depth - 1);
    if (this.depth === 0) this.dragging = false;
  };

  private onDrop = (event: DragEvent): void => {
    if (!this.carriesFiles(event)) return;
    event.preventDefault();
    this.depth = 0;
    this.dragging = false;
    const files = Array.from(event.dataTransfer?.files ?? []);
    if (!this.disabled && files.length) {
      this.dispatchEvent(new CustomEvent("hca-drop", { detail: { files }, bubbles: true, composed: true }));
    }
  };

  render() {
    if (!this.dragging) return nothing;
    return html`
      <div class="overlay ${this.disabled ? "disabled" : ""}" role="status">
        <div class="frame">
          <div class="icons"><hca-icon name="file"></hca-icon><hca-icon name="paperclip"></hca-icon></div>
          <div class="heading">${this.disabled ? "Files cannot be attached here" : this.heading}</div>
          <div class="message">${this.disabled ? this.reason : this.message}</div>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-drop-zone": HcaDropZone;
  }
}
