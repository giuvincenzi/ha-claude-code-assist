import { LitElement, css, html, nothing } from "lit";
import { customElement, property, query, state } from "lit/decorators.js";

import type { Connection } from "../../lib/connection";
import { CoreController } from "../../lib/core-controller";
import { formatDate } from "../../lib/format";
import { loadSettings } from "../../lib/settings";
import type { MemoryEntry, SettingsView } from "../../lib/types";
import "../../ui/hca-banner";
import "../../ui/hca-button";
import "../../ui/hca-confirm-dialog";
import type { HcaConfirmDialog } from "../../ui/hca-confirm-dialog";
import "../../ui/hca-empty-state";
import "../../ui/hca-input";
import type { HcaInput } from "../../ui/hca-input";
import "../../ui/hca-list-row";
import "../../ui/hca-page";
import "../../ui/hca-section";

interface MemoryList {
  entries: MemoryEntry[];
  max_entries: number;
  max_entry_length: number;
}

/** Long-term memory: its entries. Its settings are in Settings. */
@customElement("hca-memory-view")
export class HcaMemoryView extends LitElement {
  static styles = css`
    .add,
    .edit {
      display: flex;
      gap: var(--hca-space-2);
      align-items: flex-start;
    }
    .add hca-input,
    .edit hca-input {
      flex: 1;
    }
  `;

  @property({ attribute: false }) connection!: Connection;
  @state() private memory: MemoryList | null = null;
  @state() private settings: SettingsView | null = null;
  @state() private editing: number | null = null;
  @state() private error: string | null = null;
  @query("hca-confirm-dialog") private confirm!: HcaConfirmDialog;

  constructor() {
    super();
    new CoreController(this, {
      onOpen: () => this.load(),
      onEvent: (event) => {
        if (event.type === "memory_changed") this.loadEntries();
        // Turning long-term memory on or off shows or hides the warning above the entries.
        if (event.type === "settings_changed") this.loadSettings();
      },
    });
  }

  private async load(): Promise<void> {
    await this.loadEntries();
    await this.loadSettings();
  }

  private async loadSettings(): Promise<void> {
    this.settings = await loadSettings(this.connection);
  }

  private async loadEntries(): Promise<void> {
    this.memory = await this.connection.request<MemoryList>("memory/list");
  }

  private async run(action: () => Promise<unknown>): Promise<boolean> {
    this.error = null;
    try {
      await action();
      return true;
    } catch (err) {
      this.error = (err as Error).message;
      return false;
    }
  }

  private async add(): Promise<void> {
    const input = this.renderRoot.querySelector<HcaInput>("#new-entry")!;
    if (!input.value.trim()) return;
    if (await this.run(() => this.connection.request("memory/add", { text: input.value }))) input.value = "";
  }

  private async save(entry: MemoryEntry): Promise<void> {
    const input = this.renderRoot.querySelector<HcaInput>(`#edit-${entry.id}`)!;
    if (await this.run(() => this.connection.request("memory/update", { entry_id: entry.id, text: input.value }))) {
      this.editing = null;
    }
  }

  private async removeEntry(entry: MemoryEntry): Promise<void> {
    const confirmed = await this.confirm.ask({
      heading: "Remove this entry?", message: entry.text, confirmLabel: "Remove", danger: true,
    });
    if (confirmed) await this.run(() => this.connection.request("memory/remove", { entry_id: entry.id }));
  }

  private renderEntry(entry: MemoryEntry, maxLength: number) {
    if (this.editing === entry.id) {
      return html`
        <hca-list-row>
          <div slot="heading" class="edit">
            <hca-input id="edit-${entry.id}" .value=${entry.text} maxlength=${maxLength} placeholder="Entry"></hca-input>
            <hca-button variant="primary" @click=${() => this.save(entry)}>Save</hca-button>
            <hca-button variant="ghost" @click=${() => (this.editing = null)}>Cancel</hca-button>
          </div>
        </hca-list-row>
      `;
    }
    return html`
      <hca-list-row heading=${entry.text}
        detail=${`Saved by ${entry.created_by === "claude" ? "the assistant" : "you"} on ${formatDate(entry.created_at)}`}>
        <hca-button slot="end" size="sm" variant="ghost" icon="edit" @click=${() => (this.editing = entry.id)}>Edit</hca-button>
        <hca-button slot="end" size="sm" variant="ghost" icon="trash" @click=${() => this.removeEntry(entry)}>Remove</hca-button>
      </hca-list-row>
    `;
  }

  private renderEntries() {
    const memory = this.memory;
    if (!memory) return nothing;
    const off = this.settings && !this.settings.values.memory_enabled;
    return html`
      <hca-section heading="Entries"
        description=${`The assistant remembers these facts in every session. It saves one only when you ask it to remember something. You have ${memory.entries.length} of ${memory.max_entries}.`}>
        ${off ? html`<hca-banner tone="warn">Long-term memory is off, so the assistant does not use these entries. You can turn it on in Settings.</hca-banner>` : nothing}
        <div class="add">
          <hca-input id="new-entry" placeholder="Something the assistant should always know" maxlength=${memory.max_entry_length}
            @keydown=${(e: KeyboardEvent) => e.key === "Enter" && this.add()}></hca-input>
          <hca-button variant="primary" icon="plus" @click=${this.add}>Add</hca-button>
        </div>
        ${memory.entries.length
          ? html`<div>${memory.entries.map((e) => this.renderEntry(e, memory.max_entry_length))}</div>`
          : html`<hca-empty-state icon="memory" heading="Nothing remembered yet">
              Ask the assistant to remember something, or add it here.
            </hca-empty-state>`}
      </hca-section>
    `;
  }

  render() {
    return html`
      <hca-page>
        ${this.error ? html`<hca-banner tone="error">${this.error}</hca-banner>` : nothing}
        ${this.renderEntries()}
      </hca-page>
      <hca-confirm-dialog></hca-confirm-dialog>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-memory-view": HcaMemoryView;
  }
}
