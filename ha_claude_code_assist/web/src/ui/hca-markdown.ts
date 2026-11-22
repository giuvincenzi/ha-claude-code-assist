import { LitElement, css, html, nothing, type TemplateResult } from "lit";
import { customElement, property } from "lit/decorators.js";
import type { Definition, Nodes, Parents, Root } from "mdast";
import { fromMarkdown } from "mdast-util-from-markdown";
import { gfmFromMarkdown } from "mdast-util-gfm";
import { gfm } from "micromark-extension-gfm";

import "./hca-code-block";
import { base } from "./styles";

type Content = TemplateResult | string | typeof nothing;

/** Only these addresses become links: anything else (javascript:, relative paths) stays text. */
const SAFE_PROTOCOLS = new Set(["http:", "https:", "mailto:"]);

function safeUrl(url: string): string | null {
  try {
    return SAFE_PROTOCOLS.has(new URL(url).protocol) ? url : null;
  } catch {
    return null;
  }
}

function link(url: string, title: string | null | undefined, content: Content | Content[]): Content {
  const href = safeUrl(url);
  if (!href) return html`${content}`;
  return html`<a href=${href} title=${title ?? nothing} target="_blank" rel="noopener noreferrer">${content}</a>`;
}

/**
 * Markdown (CommonMark and GitHub's extensions: tables, task lists, strikethrough, autolinks),
 * drawn from the parsed tree with Lit templates. No HTML string is ever built or inserted: HTML
 * written in the text shows as text, and only http(s) and mailto addresses become links. Images
 * show as links, so nothing is loaded from other sites.
 */
@customElement("hca-markdown")
export class HcaMarkdown extends LitElement {
  static styles = [
    base,
    css`
      :host {
        display: block;
        line-height: 1.6;
        overflow-wrap: break-word;
      }
      .markdown > :first-child {
        margin-top: 0;
      }
      .markdown > :last-child {
        margin-bottom: 0;
      }
      p,
      ul,
      ol,
      blockquote,
      .table,
      hca-code-block {
        margin: 0 0 var(--hca-space-3);
      }
      p {
        white-space: pre-line;
      }
      h2,
      h3,
      h4,
      h5,
      h6 {
        margin: var(--hca-space-4) 0 var(--hca-space-2);
        font-size: var(--hca-text-md);
        font-weight: 650;
        line-height: 1.4;
      }
      h2 {
        font-size: var(--hca-text-lg);
      }
      ul,
      ol {
        padding-left: var(--hca-space-5);
      }
      li + li {
        margin-top: var(--hca-space-1);
      }
      li > p {
        margin-bottom: var(--hca-space-2);
      }
      li > ul,
      li > ol {
        margin: var(--hca-space-1) 0 0;
      }
      li.task {
        list-style: none;
      }
      li.task input {
        margin: 0 var(--hca-space-2) 0 calc(-1 * var(--hca-space-5) + var(--hca-space-1));
        vertical-align: middle;
      }
      strong {
        font-weight: 650;
      }
      code {
        padding: 1px 5px;
        border-radius: var(--hca-radius-sm);
        background: var(--hca-surface-muted);
        font-family: var(--hca-font-mono);
        font-size: 0.9em;
      }
      blockquote {
        padding-left: var(--hca-space-3);
        border-left: 3px solid var(--hca-border-strong);
        color: var(--hca-text-muted);
      }
      hr {
        margin: var(--hca-space-4) 0;
        border: none;
        border-top: 1px solid var(--hca-border);
      }
      a {
        color: var(--hca-accent);
      }
      .table {
        overflow-x: auto;
      }
      table {
        border-collapse: collapse;
        font-size: var(--hca-text-sm);
      }
      th,
      td {
        padding: var(--hca-space-1) var(--hca-space-3);
        border: 1px solid var(--hca-border);
        text-align: left;
        vertical-align: top;
      }
      th {
        background: var(--hca-surface-muted);
        font-weight: 600;
      }
      sup {
        font-size: 0.75em;
      }
      .footnote {
        font-size: var(--hca-text-sm);
        color: var(--hca-text-muted);
      }
    `,
  ];

  @property() text = "";

  /** Link and image definitions ([label]: address) used by references in the text. */
  private definitions = new Map<string, Definition>();

  render() {
    const root: Root = fromMarkdown(this.text, { extensions: [gfm()], mdastExtensions: [gfmFromMarkdown()] });
    this.definitions = new Map();
    for (const node of root.children) if (node.type === "definition") this.definitions.set(node.identifier, node);
    return html`<div class="markdown">${this.renderChildren(root)}</div>`;
  }

  private renderChildren(parent: Parents, tight = false): Content[] {
    return parent.children.map((node) => this.renderNode(node, tight));
  }

  private renderNode(node: Nodes, tight = false): Content {
    switch (node.type) {
      case "paragraph":
        // In a tight list the items' text is not wrapped in paragraphs.
        return tight ? html`${this.renderChildren(node)}` : html`<p>${this.renderChildren(node)}</p>`;
      case "heading": {
        // The page already has its own headings: an answer's headings start one level down.
        const content = this.renderChildren(node);
        switch (Math.min(node.depth + 1, 6)) {
          case 2: return html`<h2>${content}</h2>`;
          case 3: return html`<h3>${content}</h3>`;
          case 4: return html`<h4>${content}</h4>`;
          case 5: return html`<h5>${content}</h5>`;
          default: return html`<h6>${content}</h6>`;
        }
      }
      case "list": {
        const items = node.children.map((item) => this.renderNode(item, !node.spread));
        return node.ordered
          ? html`<ol start=${node.start ?? nothing}>${items}</ol>`
          : html`<ul>${items}</ul>`;
      }
      case "listItem": {
        const content = this.renderChildren(node, tight);
        if (node.checked === null || node.checked === undefined) return html`<li>${content}</li>`;
        return html`<li class="task"><input type="checkbox" disabled ?checked=${node.checked}>${content}</li>`;
      }
      case "blockquote":
        return html`<blockquote>${this.renderChildren(node)}</blockquote>`;
      case "code":
        return html`<hca-code-block code=${node.value}></hca-code-block>`;
      case "thematicBreak":
        return html`<hr>`;
      case "table": {
        // The parser gives only "left", "right", "center" or null.
        const align = (column: number) => (node.align?.[column] ? `text-align: ${node.align[column]}` : nothing);
        const [head, ...body] = node.children;
        return html`<div class="table"><table>
          <thead><tr>${head?.children.map((cell, i) => html`<th style=${align(i)}>${this.renderChildren(cell)}</th>`)}</tr></thead>
          <tbody>${body.map((row) => html`<tr>${row.children.map((cell, i) => html`<td style=${align(i)}>${this.renderChildren(cell)}</td>`)}</tr>`)}</tbody>
        </table></div>`;
      }
      case "footnoteDefinition":
        return html`<div class="footnote"><sup>${node.label ?? node.identifier}</sup> ${this.renderChildren(node, true)}</div>`;
      case "text":
        return node.value;
      case "strong":
        return html`<strong>${this.renderChildren(node)}</strong>`;
      case "emphasis":
        return html`<em>${this.renderChildren(node)}</em>`;
      case "delete":
        return html`<del>${this.renderChildren(node)}</del>`;
      case "inlineCode":
        return html`<code>${node.value}</code>`;
      case "break":
        return html`<br>`;
      case "link":
        return link(node.url, node.title, this.renderChildren(node));
      case "image":
        return link(node.url, node.title, node.alt || node.url);
      case "linkReference": {
        const definition = this.definitions.get(node.identifier);
        const content = this.renderChildren(node);
        return definition ? link(definition.url, definition.title, content) : html`${content}`;
      }
      case "imageReference": {
        const definition = this.definitions.get(node.identifier);
        return definition ? link(definition.url, definition.title, node.alt || definition.url) : node.alt ?? "";
      }
      case "footnoteReference":
        return html`<sup>${node.label ?? node.identifier}</sup>`;
      case "html":
        // HTML written in the text is shown as it is, never interpreted.
        return node.value;
      default:
        // Definitions are used by references; anything else the parser may add shows nothing.
        return nothing;
    }
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hca-markdown": HcaMarkdown;
  }
}
