import { LitElement, css, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";

import { CHANNEL_NAMES } from "../../lib/channels";
import type { Connection } from "../../lib/connection";
import { CoreController } from "../../lib/core-controller";
import { capitalize, formatDate } from "../../lib/format";
import { loadSettings, saveSettings } from "../../lib/settings";
import type { PromptSection, SettingsView } from "../../lib/types";
import { tokenProblem } from "../../lib/usage";
import "../../ui/hca-badge";
import "../../ui/hca-banner";
import "../../ui/hca-button";
import "../../ui/hca-code";
import "../../ui/hca-form-layout";
import "../../ui/hca-icon";
import "../../ui/hca-input";
import type { HcaInput } from "../../ui/hca-input";
import "../../ui/hca-page";
import "../../ui/hca-section";
import "../../ui/hca-segmented";
import type { Segment } from "../../ui/hca-segmented";
import "../../ui/hca-select";
import type { HcaSelect } from "../../ui/hca-select";
import "../../ui/hca-switch";
import type { HcaSwitch } from "../../ui/hca-switch";
import "../../ui/hca-tabs";
import type { Tab } from "../../ui/hca-tabs";
import "../../ui/hca-textarea";
import type { HcaTextarea } from "../../ui/hca-textarea";

/** Shown next to each model in the open list. */
const MODEL_DESCRIPTIONS: Record<string, string> = {
  haiku: "the fastest, and it uses the least of your subscription",
  sonnet: "balances speed and capability",
  opus: "the most capable, but slower, and it uses the most",
};

const TABS: Tab[] = [
  { id: "claude", label: "Claude Code" },
  { id: "agent", label: "Agent" },
  { id: "sessions", label: "Sessions" },
  { id: "memory", label: "Memory" },
];

/** The two prompts, by the channel whose sessions use them. */
const CHANNELS: Segment[] = Object.entries(CHANNEL_NAMES).map(([value, label]) => ({ value, label }));

/** Each section of a prompt: its name and what it is for. */
const SECTIONS: Record<string, { label: string; hint: string }> = {
  identity: { label: "Identity", hint: "Who the assistant is and whom it helps." },
  personality: { label: "Personality", hint: "Its character and the tone it speaks in." },
  capabilities: {
    label: "Capabilities",
    hint: "What it does with its own knowledge and its tools, and how it describes what it can do.",
  },
  response_style: { label: "Response style", hint: "How it writes its answers: language, length and format." },
  acting: {
    label: "Acting",
    hint: "How it carries out requests, when it asks for confirmation and how it reports the outcome.",
  },
};

/** The settings of each tab but Agent, by the option that holds them; Agent holds the sections of the prompts. */
const TAB_OPTIONS: Record<string, string[]> = {
  claude: ["model", "effort"],
  sessions: ["session_timeout_minutes", "session_retention_days"],
  memory: ["memory_enabled", "memory_max_entries", "memory_max_entry_length"],
};

type Values = Record<string, string | number | boolean>;

/**
 * Claude Code (setup token, model, effort), the agent's prompts, sessions and long-term memory,
 * in tabs. What is changed in any tab stays until it is saved or discarded: one Save, in the bar
 * at the bottom, saves every tab, and a dot marks the tabs with changes not saved yet.
 */
@customElement("hca-settings-view")
export class HcaSettingsView extends LitElement {
  static styles = css`
    :host {
      display: block;
      height: 100%;
    }
    hca-tabs {
      display: block;
    }
    .panel {
      display: grid;
      gap: var(--hca-space-4);
    }
    .panel[hidden] {
      display: none;
    }
    .pair {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: var(--hca-space-4);
    }
    .reset {
      display: flex;
    }
    .intro {
      margin: var(--hca-space-1) 0 0;
      padding-left: var(--hca-space-4);
    }
  `;

  @property({ attribute: false }) connection!: Connection;
  @state() private settings: SettingsView | null = null;
  @state() private tab = "claude";
  /** The prompt shown in Agent. */
  @state() private channel = "panel";
  /** Every setting as saved, and as edited: by option, the prompt sections included. */
  @state() private saved: Values = {};
  @state() private draft: Values = {};
  /** A new setup token, pasted and not saved yet. */
  @state() private token = "";
  @state() private error: string | null = null;
  @state() private done = false;
  @state() private saving = false;

  constructor() {
    super();
    new CoreController(this, { onOpen: () => this.load() });
  }

  private async load(): Promise<void> {
    this.show(await loadSettings(this.connection));
  }

  private show(settings: SettingsView): void {
    const v = settings.values;
    this.settings = settings;
    this.saved = {
      model: v.model,
      effort: v.effort,
      session_timeout_minutes: v.session_timeout_minutes,
      session_retention_days: v.session_retention_days,
      memory_enabled: v.memory_enabled,
      memory_max_entries: v.memory_max_entries,
      memory_max_entry_length: v.memory_max_entry_length,
      ...Object.fromEntries(this.sections(settings).map((p) => [p.option, p.text])),
    };
    this.draft = { ...this.saved };
    this.token = "";
  }

  private sections(settings: SettingsView): PromptSection[] {
    return Object.values(settings.prompts).flatMap((sections) => Object.values(sections));
  }

  private set(option: string, value: string | number | boolean): void {
    this.draft = { ...this.draft, [option]: value };
    this.done = false;
  }

  /** The options changed and not saved yet. */
  private changed(): string[] {
    return Object.keys(this.draft).filter((option) => this.draft[option] !== this.saved[option]);
  }

  private tabChanged(tab: string, changed: string[]): boolean {
    if (tab === "claude" && this.token.trim()) return true;
    const options = tab === "agent" ? this.sections(this.settings!).map((p) => p.option) : TAB_OPTIONS[tab];
    return changed.some((option) => options.includes(option));
  }

  private async save(): Promise<void> {
    const changes: Record<string, unknown> = Object.fromEntries(this.changed().map((option) => [option, this.draft[option]]));
    if (this.token.trim()) changes.claude_code_oauth_token = this.token.trim();
    this.error = null;
    this.saving = true;
    try {
      this.show(await saveSettings(this.connection, changes));
      this.done = true;
    } catch (err) {
      this.error = (err as Error).message;
    } finally {
      this.saving = false;
    }
  }

  private discard(): void {
    this.draft = { ...this.saved };
    this.token = "";
    this.error = null;
  }

  private renderTokenState(s: SettingsView) {
    const problem = tokenProblem(s.token);
    if (problem) {
      return html`<hca-badge slot="status" tone=${problem.tone} title=${problem.hint}>${capitalize(problem.label)}</hca-badge>`;
    }
    return html`<hca-badge slot="status" tone="ok"><hca-icon name="check"></hca-icon>
      Added on ${formatDate(s.token.configured_at)}. It expires around ${formatDate(s.token.expires_at)}.</hca-badge>`;
  }

  private renderClaudeCode(s: SettingsView) {
    const d = this.draft;
    return html`
      <hca-input type="password" label="Setup token" .value=${this.token}
        placeholder=${s.token.configured ? "Paste a new token to replace the current one" : "Paste your setup token"}
        @input=${(e: Event) => { this.token = (e.target as HcaInput).value; this.done = false; }}>
        ${this.renderTokenState(s)}
        <span slot="hint">To create it, run <hca-code>claude setup-token</hca-code> in a terminal on a computer where
          Claude Code is logged in with your Claude account. The token is valid for one year.</span>
      </hca-input>
      <div class="pair">
        <hca-select label="Model" value=${String(d.model)}
          .options=${s.choices.model.map((m) => ({ value: m, label: capitalize(m), description: MODEL_DESCRIPTIONS[m] }))}
          @change=${(e: Event) => this.set("model", (e.target as HcaSelect).value)}></hca-select>
        <hca-select label="Effort" value=${String(d.effort)}
          .options=${s.choices.effort.map((e) => ({ value: e, label: capitalize(e) }))}
          hint="How much the assistant thinks before answering. Higher effort gives more careful answers, but they are slower and use more of your subscription."
          @change=${(e: Event) => this.set("effort", (e.target as HcaSelect).value)}></hca-select>
      </div>
    `;
  }

  private renderAgent(s: SettingsView) {
    return html`
      <hca-banner>
        Two prompts tell the assistant who it is and how it behaves: one for the chat in this panel, one for
        Home Assistant Assist.
        <ul class="intro">
          <li>Each session uses the prompt of the place it started from.</li>
          <li>The assistant already knows its tools, its memory and how this app works.</li>
        </ul>
      </hca-banner>
      <hca-segmented label="Prompt" .options=${CHANNELS} value=${this.channel}
        @hca-change=${(e: CustomEvent<{ value: string }>) => (this.channel = e.detail.value)}></hca-segmented>
      ${Object.entries(s.prompts[this.channel]).map(([id, section]) => this.renderSection(id, section))}
    `;
  }

  private renderSection(id: string, section: PromptSection) {
    const text = String(this.draft[section.option]);
    const isDefault = !text.trim() || text.trim() === section.default;
    return html`
      <hca-textarea label=${SECTIONS[id]?.label ?? id} hint=${SECTIONS[id]?.hint ?? ""} rows="8" .value=${text}
        @input=${(e: Event) => this.set(section.option, (e.target as HcaTextarea).value)}></hca-textarea>
      <div class="reset">
        <hca-button size="sm" ?disabled=${isDefault}
          @click=${() => this.set(section.option, section.default)}>Reset to default</hca-button>
      </div>
    `;
  }

  private number(option: string) {
    return (e: Event) => this.set(option, Number((e.target as HcaInput).value));
  }

  private renderSessions() {
    const d = this.draft;
    return html`
      <hca-input type="number" label="Timeout in minutes" min="1" max="1440"
        .value=${String(d.session_timeout_minutes)} @input=${this.number("session_timeout_minutes")}
        hint="A session ends after this many minutes without messages. The next message starts a new session, which remembers only what is in long-term memory. A longer session remembers more, and every answer reads all of it, which uses a little more of your subscription."></hca-input>
      <hca-input type="number" label="Days to keep sessions" min="1" max="3650"
        .value=${String(d.session_retention_days)} @input=${this.number("session_retention_days")}
        hint="Sessions with no messages for longer than this are deleted, together with their messages. Long-term memory is not affected."></hca-input>
    `;
  }

  private renderMemory() {
    const d = this.draft;
    return html`
      <hca-switch label="Long-term memory" ?checked=${Boolean(d.memory_enabled)}
        @change=${(e: Event) => this.set("memory_enabled", (e.target as HcaSwitch).checked)}
        hint="Lets the assistant remember facts across sessions. When it is off, the assistant neither reads nor saves them."></hca-switch>
      <div class="pair">
        <hca-input type="number" label="Maximum entries" min="1" max="1000"
          .value=${String(d.memory_max_entries)} @input=${this.number("memory_max_entries")}
          hint="When the memory is full, the assistant tells you, and nothing more is saved until you remove an entry."></hca-input>
        <hca-input type="number" label="Maximum entry length" min="50" max="5000"
          .value=${String(d.memory_max_entry_length)} @input=${this.number("memory_max_entry_length")}
          hint="The longest a single entry can be, in characters."></hca-input>
      </div>
    `;
  }

  render() {
    const s = this.settings;
    if (!s) return nothing;
    const changed = this.changed();
    const dirty = changed.length > 0 || Boolean(this.token.trim());
    const tabs = TABS.map((tab) => this.tabChanged(tab.id, changed) ? { ...tab, mark: "It has changes that are not saved." } : tab);
    const [message, tone] = this.error ? [this.error, "error"]
      : dirty ? ["You have changes that are not saved.", "neutral"]
      : this.done ? ["Saved. New sessions will use the new settings.", "ok"]
      : ["", "neutral"];
    const panel = (id: string, label: string, content: unknown) =>
      html`<div class="panel" role="tabpanel" aria-label=${label} ?hidden=${this.tab !== id}>${content}</div>`;
    return html`
      <hca-form-layout message=${message} tone=${tone}>
        <hca-page>
          <hca-section>
            <hca-tabs label="Settings" .tabs=${tabs} selected=${this.tab}
              @hca-select=${(e: CustomEvent<{ id: string }>) => (this.tab = e.detail.id)}></hca-tabs>
            ${panel("claude", "Claude Code", this.renderClaudeCode(s))}
            ${panel("agent", "Agent", this.renderAgent(s))}
            ${panel("sessions", "Sessions", this.renderSessions())}
            ${panel("memory", "Memory", this.renderMemory())}
          </hca-section>
        </hca-page>
        <hca-button slot="actions" ?disabled=${!dirty || this.saving} @click=${this.discard}>Discard</hca-button>
        <hca-button slot="actions" variant="primary" ?disabled=${!dirty} ?loading=${this.saving} @click=${this.save}>Save</hca-button>
      </hca-form-layout>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-settings-view": HcaSettingsView;
  }
}
