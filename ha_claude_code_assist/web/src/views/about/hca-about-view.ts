import { LitElement, css, html, nothing } from "lit";
import { customElement, property } from "lit/decorators.js";

import type { Status } from "../../lib/types";
import "../../ui/hca-banner";
import "../../ui/hca-button";
import "../../ui/hca-page";
import "../../ui/hca-property-list";
import type { Property } from "../../ui/hca-property-list";
import "../../ui/hca-section";

/**
 * What the app is, its links on GitHub, and the versions of the app, its integration and Claude
 * Code, with what to update when the app and its integration are not the same version. Everything
 * comes from the status the header already reads.
 */
@customElement("hca-about-view")
export class HcaAboutView extends LitElement {
  static styles = css`
    .links {
      display: flex;
      flex-wrap: wrap;
      gap: var(--hca-space-2);
    }
  `;

  @property({ attribute: false }) status: Status | null = null;

  private versions(s: Status): Property[] {
    const integration = !s.integration.known
      ? "Not set up"
      : (s.integration.version ?? "An older version, which does not report it");
    return [
      { label: "App", value: s.app.version ?? "Unknown" },
      { label: "Integration", value: integration, hint: "The integration that last talked to the app." },
      { label: "Claude Code", value: s.claude_code_version ?? "Not found" },
    ];
  }

  private renderLinks(url: string) {
    return html`
      <div class="links">
        <hca-button icon="book" href=${`${url}/blob/main/ha_claude_code_assist/DOCS.md`}>Documentation</hca-button>
        <hca-button icon="history" href=${`${url}/blob/main/ha_claude_code_assist/CHANGELOG.md`}>Changelog</hca-button>
        <hca-button icon="alert" href=${`${url}/issues/new`}>Report an issue</hca-button>
        <hca-button icon="star" variant="primary" href=${url}>Star on GitHub</hca-button>
      </div>
    `;
  }

  render() {
    const s = this.status;
    if (!s) return nothing;
    return html`
      <hca-page>
        <hca-section heading="HA Claude Code Assist" description=${s.app.description ?? ""}>
          <hca-banner>
            Unofficial project, not affiliated with, sponsored or endorsed by Anthropic. Claude and Claude Code
            are trademarks of Anthropic.
          </hca-banner>
          ${s.app.url ? this.renderLinks(s.app.url) : nothing}
        </hca-section>
        <hca-section heading="Versions"
          description="The app and its integration come from the same release, so they are meant to have the same version.">
          ${s.version_problem ? html`<hca-banner tone="warn">${s.version_problem}</hca-banner>` : nothing}
          <hca-property-list .items=${this.versions(s)}></hca-property-list>
        </hca-section>
      </hca-page>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-about-view": HcaAboutView;
  }
}
