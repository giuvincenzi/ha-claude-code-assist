import { LitElement, css, svg } from "lit";
import { customElement, property } from "lit/decorators.js";

/** Stroke icons on a 24×24 grid; only the ones the app uses. */
const PATHS = {
  alert: "M12 3 2 20h20L12 3Z M12 10v4 M12 17h.01",
  chat: "M4 5h16v11H9l-5 4V5Z",
  check: "M5 12.5 10 17l9-10",
  "chevron-right": "M9 6l6 6-6 6",
  download: "M12 4v11 M7 10l5 5 5-5 M5 20h14",
  edit: "M4 20h4L19 9l-4-4L4 16v4Z M13.5 6.5l4 4",
  file: "M14 3H6v18h12V7l-4-4Z M14 3v4h4 M9 13h6 M9 17h6",
  history: "M3 12a9 9 0 1 0 3-6.7 M3 4v5h5 M12 7v5l3 2",
  paperclip: "M21 11.5 12.6 20a5 5 0 0 1-7.1-7.1L14 4.4a3.5 3.5 0 0 1 5 5l-8.5 8.5a2 2 0 0 1-2.9-2.9L15.4 7.2",
  memory: "M9 4a3 3 0 0 0-3 3v1a3 3 0 0 0-2 5 3 3 0 0 0 2 5v1a3 3 0 0 0 6 0V4a3 3 0 0 0-3 0Z M15 4a3 3 0 0 1 3 3v1a3 3 0 0 1 2 5 3 3 0 0 1-2 5v1a3 3 0 0 1-6 0",
  plus: "M12 5v14 M5 12h14",
  send: "M4 12 20 4l-6 16-3-7-7-1Z M11 13l9-9",
  settings: "M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z",
  tool: "M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.6 2.6-2.4-.6-.6-2.4 2.6-2.6Z",
  trash: "M4 7h16 M10 11v6 M14 11v6 M6 7l1 13h10l1-13 M9 7V4h6v3",
  x: "M6 6l12 12 M18 6 6 18",
} as const;

export type IconName = keyof typeof PATHS;

@customElement("hca-icon")
export class HcaIcon extends LitElement {
  static styles = css`
    :host {
      display: inline-flex;
      width: var(--hca-icon-size, 18px);
      height: var(--hca-icon-size, 18px);
      flex-shrink: 0;
    }
    svg {
      width: 100%;
      height: 100%;
    }
  `;

  @property() name: IconName = "chat";

  render() {
    return svg`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
      stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d=${PATHS[this.name]} /></svg>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-icon": HcaIcon;
  }
}
