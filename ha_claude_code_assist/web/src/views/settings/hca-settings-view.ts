import { LitElement, css, html, nothing } from "lit";
import { customElement, property, query, state } from "lit/decorators.js";

import type { Connection } from "../../lib/connection";
import { CoreController } from "../../lib/core-controller";
import { capitalize, formatDate } from "../../lib/format";
import { loadSettings, saveSettings } from "../../lib/settings";
import type { SettingsView } from "../../lib/types";
import { tokenProblem } from "../../lib/usage";
import "../../ui/hca-badge";
import "../../ui/hca-banner";
import "../../ui/hca-button";
import "../../ui/hca-code";
import "../../ui/hca-icon";
import "../../ui/hca-input";
import type { HcaInput } from "../../ui/hca-input";
import "../../ui/hca-page";
import "../../ui/hca-section";
import "../../ui/hca-select";
import type { HcaSelect } from "../../ui/hca-select";
import "../../ui/hca-switch";
import type { HcaSwitch } from "../../ui/hca-switch";
import "../../ui/hca-tabs";
import type { Tab } from "../../ui/hca-tabs";

/** Shown next to each model in the open list. */
const MODEL_DESCRIPTIONS: Record<string, string> = {
  haiku: "the fastest, and it uses the least of your subscription",
  sonnet: "balances speed and capability",
  opus: "the most capable, but slower, and it uses the most",
};

const TABS: Tab[] = [
  { id: "claude", label: "Claude Code" },
  { id: "sessions", label: "Sessions" },
  { id: "memory", label: "Memory" },
];

/**
 * Claude Code (setup token, model, effort), sessions and long-term memory, in tabs. Every tab
 * stays on the page while hidden, so one Save keeps what was changed in each of them.
 */
@customElement("hca-settings-view")
export class HcaSettingsView extends LitElement {
  static styles = css`
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
    .actions {
      display: flex;
      gap: var(--hca-space-3);
      align-items: center;
    }
  `;

  @property({ attribute: false }) connection!: Connection;
  @state() private settings: SettingsView | null = null;
  @state() private tab = "claude";
  @state() private error: string | null = null;
  @state() private saved = false;
  @state() private saving = false;
  @query("#token") private token!: HcaInput;
  @query("#model") private model!: HcaSelect;
  @query("#effort") private effort!: HcaSelect;
  @query("#timeout") private timeout!: HcaInput;
  @query("#retention") private retention!: HcaInput;
  @query("#memory-enabled") private memoryEnabled!: HcaSwitch;
  @query("#max-entries") private maxEntries!: HcaInput;
  @query("#max-length") private maxLength!: HcaInput;

  constructor() {
    super();
    new CoreController(this, { onOpen: () => this.load() });
  }

  private async load(): Promise<void> {
    this.settings = await loadSettings(this.connection);
  }

  private async save(): Promise<void> {
    this.error = null;
    this.saved = false;
    const changes: Record<string, unknown> = {
      model: this.model.value,
      effort: this.effort.value,
      session_timeout_minutes: Number(this.timeout.value),
      session_retention_days: Number(this.retention.value),
      memory_enabled: this.memoryEnabled.checked,
      memory_max_entries: Number(this.maxEntries.value),
      memory_max_entry_length: Number(this.maxLength.value),
    };
    if (this.token.value.trim()) changes.claude_code_oauth_token = this.token.value.trim();
    this.saving = true;
    try {
      this.settings = await saveSettings(this.connection, changes);
      this.token.value = "";
      this.saved = true;
    } catch (err) {
      this.error = (err as Error).message;
    } finally {
      this.saving = false;
    }
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
    const v = s.values;
    return html`
      <hca-input id="token" type="password" label="Setup token"
        placeholder=${s.token.configured ? "Paste a new token to replace the current one" : "Paste your setup token"}>
        ${this.renderTokenState(s)}
        <span slot="hint">To create it, run <hca-code>claude setup-token</hca-code> in a terminal on a computer where
          Claude Code is logged in with your Claude account. The token is valid for one year.</span>
      </hca-input>
      <div class="pair">
        <hca-select id="model" label="Model" value=${v.model}
          .options=${s.choices.model.map((m) => ({ value: m, label: capitalize(m), description: MODEL_DESCRIPTIONS[m] }))}></hca-select>
        <hca-select id="effort" label="Effort" value=${v.effort}
          .options=${s.choices.effort.map((e) => ({ value: e, label: capitalize(e) }))}
          hint="How much the assistant thinks before answering. Higher effort gives more careful answers, but they are slower and use more of your subscription."></hca-select>
      </div>
    `;
  }

  private renderSessions(s: SettingsView) {
    return html`
      <hca-input id="timeout" type="number" label="Timeout in minutes" min="1" max="1440"
        .value=${String(s.values.session_timeout_minutes)}
        hint="A session ends after this many minutes without messages. The next message starts a new session, which remembers only what is in long-term memory. A longer session remembers more, and every answer reads all of it, which uses a little more of your subscription."></hca-input>
      <hca-input id="retention" type="number" label="Days to keep sessions" min="1" max="3650"
        .value=${String(s.values.session_retention_days)}
        hint="Sessions with no messages for longer than this are deleted, together with their messages. Long-term memory is not affected."></hca-input>
    `;
  }

  private renderMemory(s: SettingsView) {
    const v = s.values;
    return html`
      <hca-switch id="memory-enabled" label="Long-term memory" ?checked=${v.memory_enabled}
        hint="Lets the assistant remember facts across sessions. When it is off, the assistant neither reads nor saves them."></hca-switch>
      <div class="pair">
        <hca-input id="max-entries" type="number" label="Maximum entries" min="1" max="1000"
          .value=${String(v.memory_max_entries)}
          hint="When the memory is full, the assistant tells you, and nothing more is saved until you remove an entry."></hca-input>
        <hca-input id="max-length" type="number" label="Maximum entry length" min="50" max="5000"
          .value=${String(v.memory_max_entry_length)} hint="The longest a single entry can be, in characters."></hca-input>
      </div>
    `;
  }

  render() {
    const s = this.settings;
    if (!s) return nothing;
    const panel = (id: string, label: string, content: unknown) =>
      html`<div class="panel" role="tabpanel" aria-label=${label} ?hidden=${this.tab !== id}>${content}</div>`;
    return html`
      <hca-page>
        ${this.error ? html`<hca-banner tone="error">${this.error}</hca-banner>` : nothing}
        <hca-section>
          <hca-tabs label="Settings" .tabs=${TABS} selected=${this.tab}
            @hca-select=${(e: CustomEvent<{ id: string }>) => (this.tab = e.detail.id)}></hca-tabs>
          ${panel("claude", "Claude Code", this.renderClaudeCode(s))}
          ${panel("sessions", "Sessions", this.renderSessions(s))}
          ${panel("memory", "Memory", this.renderMemory(s))}
        </hca-section>
        <div class="actions">
          <hca-button variant="primary" ?loading=${this.saving} @click=${this.save}>Save</hca-button>
          ${this.saved ? html`<hca-badge tone="ok">Saved. New sessions will use the new settings.</hca-badge>` : nothing}
        </div>
      </hca-page>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-settings-view": HcaSettingsView;
  }
}
