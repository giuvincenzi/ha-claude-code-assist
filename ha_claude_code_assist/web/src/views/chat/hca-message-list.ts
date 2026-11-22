import { LitElement, css, html, nothing } from "lit";
import { customElement, property, query } from "lit/decorators.js";

import { attachmentDownloadUrl, attachmentUrl } from "../../lib/attachments";
import { saveFile } from "../../lib/files";
import { formatClock, formatSeconds } from "../../lib/format";
import type { ChatAttachment, ChatItem } from "../../lib/types";
import "../../ui/hca-attachment";
import "../../ui/hca-banner";
import "../../ui/hca-lightbox";
import type { HcaLightbox } from "../../ui/hca-lightbox";
import "../../ui/hca-code-block";
import "../../ui/hca-message";
import "../../ui/hca-tool-call";
import "../../ui/hca-typing";

const ASSISTANT = "HA Claude Code Assist";

/** "mcp__home-assistant__HassTurnOff" → "HassTurnOff from home-assistant"; internal and built-in
 * tools by name. */
function toolLabel(name: string): string {
  const [, server, tool] = name.match(/^mcp__(.+?)__(.+)$/) ?? [];
  if (!server) return name;
  return server === "ha_cca" ? tool.replace(/^ha_cca_/, "").replaceAll("_", " ") : `${tool} from ${server}`;
}

function meta(...parts: Array<string | null | undefined>): string {
  return parts.filter(Boolean).join(" · ");
}

/** A conversation, in order: the user's messages, the tools the assistant used, its answers. */
@customElement("hca-message-list")
export class HcaMessageList extends LitElement {
  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
    }
    hca-banner {
      margin-top: var(--hca-space-3);
    }
    .attachments {
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: var(--hca-space-2);
      margin-bottom: var(--hca-space-2);
    }
  `;

  @property({ attribute: false }) items: ChatItem[] = [];
  @property() userName = "You";
  /** Our id of the session, to show the pictures attached to its messages. */
  @property() sessionId = "";
  @query("hca-lightbox") private lightbox!: HcaLightbox;
  @property({ type: Boolean }) busy = false;

  private src(a: ChatAttachment): string {
    return !a.image ? "" : a.url ?? (this.sessionId ? attachmentUrl(this.sessionId, a.name) : "");
  }

  /** A picture opens over the page; another file is saved. */
  private open(a: ChatAttachment): void {
    const download = a.url ?? (this.sessionId ? attachmentDownloadUrl(this.sessionId, a.name) : "");
    if (!download) return;
    if (a.image) this.lightbox.show(this.src(a), a.name, download);
    else saveFile(download, a.name);
  }

  private renderAttachments(files: ChatAttachment[]) {
    return html`<div slot="attachments" class="attachments">
      ${files.map((a) => html`<hca-attachment name=${a.name} src=${this.src(a)} ?loading=${a.loading} ?failed=${a.failed}
        @hca-open=${() => this.open(a)}></hca-attachment>`)}
    </div>`;
  }

  render() {
    const last = this.items[this.items.length - 1];
    return html`
      ${this.items.map((item, index) => {
        // The assistant's name and time head its turn once, on the first item after the user's message.
        const opensTurn = index === 0 || this.items[index - 1].kind === "user";
        switch (item.kind) {
          case "user":
            return html`<hca-message from="user" .text=${item.text}
              meta=${meta(this.userName, formatClock(item.timestamp))}>
              ${item.attachments?.length ? this.renderAttachments(item.attachments) : nothing}
            </hca-message>`;
          case "assistant":
            return item.text
              ? html`<hca-message .text=${item.text}
                  meta=${opensTurn ? meta(ASSISTANT, formatClock(item.timestamp)) : ""}
                  footer=${item.duration_ms !== undefined ? formatSeconds(item.duration_ms) : ""}></hca-message>`
              : nothing;
          case "tool":
            return html`
              ${opensTurn ? html`<hca-message meta=${meta(ASSISTANT, formatClock(item.timestamp))}></hca-message>` : nothing}
              <hca-tool-call label=${toolLabel(item.name)}
                status=${item.result === null ? "running" : item.is_error ? "failed" : "ok"}>
                <hca-code-block .code=${JSON.stringify(item.input, null, 2)}></hca-code-block>
                ${item.result !== null ? html`<hca-code-block .code=${item.result}></hca-code-block>` : nothing}
              </hca-tool-call>`;
          case "error":
            return html`<hca-banner tone="error">${item.text}</hca-banner>`;
        }
      })}
      ${this.busy && (last?.kind === "user" || last?.kind === "tool") ? html`<hca-typing></hca-typing>` : nothing}
      <hca-lightbox></hca-lightbox>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-message-list": HcaMessageList;
  }
}
