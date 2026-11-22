import { LitElement, css, html, nothing } from "lit";
import { customElement, property, query, state } from "lit/decorators.js";

import type { Connection } from "../../lib/connection";
import { CoreController } from "../../lib/core-controller";
import { loadSettings, saveSettings } from "../../lib/settings";
import type { SettingsView } from "../../lib/types";
import "../../ui/hca-badge";
import "../../ui/hca-banner";
import "../../ui/hca-button";
import "../../ui/hca-card";
import "../../ui/hca-empty-state";
import "../../ui/hca-icon-button";
import "../../ui/hca-input";
import "../../ui/hca-page";
import "../../ui/hca-section";
import "../../ui/hca-spinner";
import "../../ui/hca-switch";
import type { HcaSwitch } from "../../ui/hca-switch";
import "../../ui/hca-textarea";

const RESERVED_SERVER = "ha_cca";
const SERVER_NAME = /^[A-Za-z0-9_-]+$/;
const NEW_SERVER_CONFIG = JSON.stringify({ type: "http", url: "" }, null, 2);

type CheckResult = { ok: true; tools: number } | { ok: false; error: string };

interface ServerRow {
  id: number;
  name: string;
  config: string;
  error?: string;
  check?: CheckResult | "checking";
}

/** What the assistant can use: web search and the MCP servers, one card each, checked after saving. */
@customElement("hca-tools-view")
export class HcaToolsView extends LitElement {
  static styles = css`
    .servers {
      display: grid;
      gap: var(--hca-space-3);
    }
    .server-head {
      display: flex;
      gap: var(--hca-space-2);
      align-items: flex-end;
    }
    .server-head hca-input {
      flex: 1;
    }
    .actions {
      display: flex;
      gap: var(--hca-space-3);
      align-items: center;
    }
  `;

  @property({ attribute: false }) connection!: Connection;
  @state() private settings: SettingsView | null = null;
  @state() private servers: ServerRow[] = [];
  @state() private error: string | null = null;
  @state() private saved = false;
  @state() private saving = false;
  @query("#web-search") private webSearch!: HcaSwitch;
  @query("#read-files") private readFiles!: HcaSwitch;
  private nextId = 1;

  constructor() {
    super();
    new CoreController(this, { onOpen: () => this.load() });
  }

  private async load(): Promise<void> {
    this.show(await loadSettings(this.connection));
  }

  /** The saved settings, with the MCP servers as one editable card each. */
  private show(settings: SettingsView): void {
    this.settings = settings;
    let servers: Record<string, unknown> = {};
    try {
      servers = JSON.parse(settings.values.mcp_servers).mcpServers ?? {};
    } catch {
      this.error = "The saved MCP servers are not valid JSON. Fix them in the app's Configuration tab in Home Assistant.";
    }
    this.servers = Object.entries(servers).map(([name, config]) => ({
      id: this.nextId++, name, config: JSON.stringify(config, null, 2),
    }));
  }

  private updateServer(id: number, changes: Partial<ServerRow>): void {
    this.servers = this.servers.map((s) => (s.id === id ? { ...s, ...changes, error: undefined, check: undefined } : s));
    this.saved = false;
  }

  private addServer(): void {
    this.servers = [...this.servers, { id: this.nextId++, name: "", config: NEW_SERVER_CONFIG }];
  }

  private removeServer(id: number): void {
    this.servers = this.servers.filter((s) => s.id !== id);
    this.saved = false;
  }

  /** Validates every card; returns the mcpServers object, or null when one needs fixing. */
  private collectServers(): Record<string, unknown> | null {
    const names = new Set<string>();
    const result: Record<string, unknown> = {};
    let valid = true;
    this.servers = this.servers.map((server) => {
      const name = server.name.trim();
      let error: string | undefined;
      let config: unknown;
      try {
        config = JSON.parse(server.config);
      } catch (err) {
        error = `The configuration is not valid JSON. ${(err as Error).message}`;
      }
      if (!name) error = "Give the server a name.";
      else if (!SERVER_NAME.test(name)) error = "The name can contain only letters, digits, hyphens and underscores.";
      else if (name === RESERVED_SERVER) error = `The name "${RESERVED_SERVER}" is reserved for the app. Choose another name.`;
      else if (names.has(name)) error = "Another server has the same name.";
      else if (!error && (typeof config !== "object" || config === null || Array.isArray(config))) {
        error = 'The configuration must be a JSON object, such as {"type": "http", "url": "…"}.';
      }
      names.add(name);
      if (error) valid = false;
      else result[name] = config;
      return { ...server, name, error, check: undefined };
    });
    return valid ? result : null;
  }

  private async save(): Promise<void> {
    this.error = null;
    this.saved = false;
    const servers = this.collectServers();
    if (!servers) {
      this.error = "Some MCP servers need fixing, so nothing was saved.";
      return;
    }
    this.saving = true;
    try {
      this.show(await saveSettings(this.connection, {
        web_search: this.webSearch.checked,
        read_files: this.readFiles.checked,
        mcp_servers: JSON.stringify({ mcpServers: servers }),
      }));
      this.saved = true;
      await this.checkServers();
    } catch (err) {
      this.error = (err as Error).message;
    } finally {
      this.saving = false;
    }
  }

  /** Connects to every saved server and shows what it answered on its card. */
  private async checkServers(): Promise<void> {
    if (!this.servers.length) return;
    this.servers = this.servers.map((s) => ({ ...s, check: "checking" }));
    const results = await this.connection.request<Record<string, CheckResult>>("mcp/check");
    this.servers = this.servers.map((s) => ({ ...s, check: results[s.name] }));
  }

  private renderStatus(server: ServerRow) {
    if (server.error) return html`<hca-banner tone="error">${server.error}</hca-banner>`;
    if (server.check === "checking") return html`<hca-badge><hca-spinner></hca-spinner> Checking the connection…</hca-badge>`;
    if (!server.check) return nothing;
    return server.check.ok
      ? html`<div><hca-badge tone="ok">Connected, with ${server.check.tools} tool${server.check.tools === 1 ? "" : "s"}</hca-badge></div>`
      : html`<hca-banner tone="error">${server.check.error}</hca-banner>`;
  }

  private renderServer(server: ServerRow) {
    return html`
      <hca-card>
        <div class="server-head">
          <hca-input label="Name" placeholder="home-assistant" .value=${server.name}
            @input=${(e: Event) => this.updateServer(server.id, { name: (e.currentTarget as HTMLInputElement).value })}></hca-input>
          <hca-icon-button icon="trash" label="Remove this server" @click=${() => this.removeServer(server.id)}></hca-icon-button>
        </div>
        <hca-textarea code rows="7" label="Configuration" .value=${server.config}
          @input=${(e: Event) => this.updateServer(server.id, { config: (e.currentTarget as HTMLTextAreaElement).value })}></hca-textarea>
        ${this.renderStatus(server)}
      </hca-card>
    `;
  }

  render() {
    const v = this.settings?.values;
    if (!v) return nothing;
    return html`
      <hca-page>
        ${this.error ? html`<hca-banner tone="error">${this.error}</hca-banner>` : nothing}
        <hca-section heading="Built-in tools">
          <hca-switch id="web-search" label="Web search" ?checked=${v.web_search}
            hint="Lets the assistant search the web and read web pages, for news and up-to-date information."></hca-switch>
          <hca-switch id="read-files" label="Read files" ?checked=${v.read_files}
            hint="Lets the assistant open images, PDFs and text files. It can read only the files of its own session."></hca-switch>
        </hca-section>
        <hca-section heading="MCP servers">
          <hca-button slot="actions" icon="plus" @click=${this.addServer}>Add MCP server</hca-button>
          ${this.servers.length
            ? html`<div class="servers">${this.servers.map((s) => this.renderServer(s))}</div>`
            : html`<hca-empty-state icon="tool" heading="No MCP servers">
                Add Home Assistant's MCP Server to let the assistant see and control your home.
              </hca-empty-state>`}
        </hca-section>
        <div class="actions">
          <hca-button variant="primary" ?loading=${this.saving} @click=${this.save}>Save</hca-button>
          ${this.saved ? html`<hca-badge tone="ok">Saved. New sessions will use the new tools.</hca-badge>` : nothing}
        </div>
      </hca-page>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-tools-view": HcaToolsView;
  }
}
