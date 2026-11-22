import { LitElement, css, html } from "lit";
import { customElement, state } from "lit/decorators.js";

import "./layout/hca-app-header";
import "./layout/hca-connection-banner";
import { coreConnection } from "./lib/connection";
import { CoreController } from "./lib/core-controller";
import type { Status } from "./lib/types";
import type { Tab } from "./ui/hca-tabs";
import "./views/chat/hca-chat-view";
import "./views/memory/hca-memory-view";
import "./views/sessions/hca-sessions-view";
import "./views/settings/hca-settings-view";
import "./views/tools/hca-tools-view";

const TABS: Tab[] = [
  { id: "chat", label: "Chat", icon: "chat" },
  { id: "memory", label: "Memory", icon: "memory" },
  { id: "tools", label: "Tools", icon: "tool" },
  { id: "sessions", label: "Sessions", icon: "history" },
  { id: "settings", label: "Settings", icon: "settings" },
];

/** The panel: header with tabs and status, then the selected view. */
@customElement("hca-app")
export class HcaApp extends LitElement {
  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      height: 100vh;
    }
    .content {
      position: relative;
      flex: 1;
      min-height: 0;
      display: flex;
      flex-direction: column;
    }
    main {
      flex: 1;
      min-height: 0;
      overflow: auto;
    }
    /* These views scroll inside their own layout. */
    main.chat,
    main.sessions {
      overflow: hidden;
    }
  `;

  readonly connection = coreConnection();
  @state() private tab = "chat";
  @state() private status: Status | null = null;

  constructor() {
    super();
    new CoreController(this, {
      onOpen: () => this.loadStatus(),
      // What the status bar shows changes with the sessions and the settings, from any panel.
      onEvent: (event) => {
        if (["session_updated", "session_deleted", "settings_changed"].includes(event.type)) this.loadStatus();
      },
    });
  }

  private async loadStatus(): Promise<void> {
    this.status = await this.connection.request<Status>("status/get");
  }

  private renderView() {
    switch (this.tab) {
      case "sessions":
        return html`<hca-sessions-view .connection=${this.connection}></hca-sessions-view>`;
      case "memory":
        return html`<hca-memory-view .connection=${this.connection}></hca-memory-view>`;
      case "tools":
        return html`<hca-tools-view .connection=${this.connection}></hca-tools-view>`;
      case "settings":
        return html`<hca-settings-view .connection=${this.connection}></hca-settings-view>`;
      default:
        return html`<hca-chat-view .connection=${this.connection}></hca-chat-view>`;
    }
  }

  render() {
    return html`
      <hca-app-header .tabs=${TABS} selected=${this.tab} .status=${this.status}
        @hca-select=${(e: CustomEvent<{ id: string }>) => (this.tab = e.detail.id)}></hca-app-header>
      <div class="content">
        <main class=${this.tab}>${this.renderView()}</main>
        <hca-connection-banner .state=${this.connection.state}></hca-connection-banner>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-app": HcaApp;
  }
}
