import { LitElement, css, html, nothing } from "lit";
import { customElement, property } from "lit/decorators.js";

import { formatDate } from "../lib/format";
import type { Status } from "../lib/types";
import { tokenProblem } from "../lib/usage";
import "../ui/hca-badge";
import "../ui/hca-tabs";
import type { Tab } from "../ui/hca-tabs";
import { base } from "../ui/styles";

/**
 * The app's top bar: name, tabs, and the state of the setup token, the MCP servers and the
 * sessions, after a warning when the app and its integration need an update to match.
 */
@customElement("hca-app-header")
export class HcaAppHeader extends LitElement {
  static styles = [
    base,
    css`
      :host {
        display: block;
        background: var(--hca-surface);
        border-bottom: 1px solid var(--hca-border);
      }
      /* Full width: name on the left, tabs in the middle, status on the right. */
      .bar {
        display: grid;
        grid-template-columns: 1fr auto 1fr;
        align-items: center;
        gap: var(--hca-space-4);
        padding: var(--hca-space-2) var(--hca-space-4);
      }
      h1 {
        margin: 0;
        font-size: var(--hca-text-lg);
        font-weight: 700;
        white-space: nowrap;
      }
      hca-tabs {
        min-width: 0;
      }
      .status {
        display: flex;
        flex-wrap: wrap;
        justify-content: flex-end;
        gap: var(--hca-space-1);
      }
      @media (max-width: 900px) {
        .bar {
          grid-template-columns: 1fr auto;
        }
        hca-tabs {
          grid-column: 1 / -1;
          grid-row: 2;
        }
      }
      /* On phones Home Assistant's own bar already shows the panel's name. */
      @media (max-width: 600px) {
        h1 {
          display: none;
        }
        .status {
          grid-column: 1 / -1;
          justify-content: flex-start;
        }
      }
    `,
  ];

  @property({ attribute: false }) tabs: Tab[] = [];
  @property() selected = "";
  @property({ attribute: false }) status: Status | null = null;

  private renderStatus() {
    const s = this.status;
    if (!s) return nothing;
    const problem = tokenProblem({ ...s.token, rejected_at: s.token_rejected_at });
    const servers = s.mcp_servers.length;
    return html`
      ${s.version_problem ? html`<hca-badge tone="warn" title=${s.version_problem}>Update needed</hca-badge>` : nothing}
      ${problem
        ? html`<hca-badge tone=${problem.tone} title=${problem.hint}>Setup token ${problem.label}</hca-badge>`
        : html`<hca-badge tone="ok" title=${`The setup token is set. It expires around ${formatDate(s.token.expires_at)}.`}>Setup token</hca-badge>`}
      <hca-badge tone=${servers ? "accent" : "neutral"} title=${s.mcp_servers.join(", ") || "Add MCP servers in Tools."}>
        ${servers ? `${servers} MCP server${servers > 1 ? "s" : ""}` : "No MCP servers"}
      </hca-badge>
      <hca-badge title=${s.claude_code_version ? `Claude Code ${s.claude_code_version}` : "Claude Code was not found."}>
        ${s.active_sessions} active session${s.active_sessions === 1 ? "" : "s"}
      </hca-badge>
    `;
  }

  render() {
    return html`
      <div class="bar">
        <h1>HA Claude Code Assist</h1>
        <hca-tabs label="Sections" .tabs=${this.tabs} selected=${this.selected}></hca-tabs>
        <div class="status">${this.renderStatus()}</div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-app-header": HcaAppHeader;
  }
}
