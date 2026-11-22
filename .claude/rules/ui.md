---
paths:
  - "ha_claude_code_assist/web/**"
---

# Panel

How the panel (`web/`) is built and must look.

- Lit and TypeScript, built by Vite in the Dockerfile; the runtime dependencies are Lit and the
  markdown parser (`mdast-util-from-markdown` with GFM), and the panel needs no internet at
  runtime (no CDN, no web fonts).
- Never build or insert HTML from strings (`unsafeHTML`, `innerHTML`): answers can carry text
  from the web. Markdown is drawn from the parsed tree with Lit templates (`ui/hca-markdown.ts`).
- `src/ui/`: the reusable components (`hca-*`), generic, with no knowledge of the app's data.
  They are the only place that defines how things look, and they build on native elements
  (`button`, `input`, `select`, `dialog`, `details`) for behaviour and accessibility.
- `src/views/`: one folder per tab, composed of `ui/` components. Their CSS is layout only
  (flex, grid, gaps from the tokens): a new visual need becomes a component in `ui/`.
- `src/lib/`: data and the connection to the core, without UI. A view connects through
  `CoreController`, which reloads on reconnect and stops listening when the view leaves the page.
- `src/theme.css` holds the design tokens (`--hca-*`: colours with their dark variant, spacing,
  radii, type); components use only these variables, never literal colours or sizes.
- Pages sit in `hca-page`, centred with a maximum width (narrow for the chat).
- Ingress serves the panel under a path of its own: only relative URLs (`base: "./"`,
  `new URL("ws", location.href)`).
- Home Assistant is often opened over plain HTTP: no API that needs a secure context
  (`crypto.randomUUID`).
- Motion respects `prefers-reduced-motion`.
- A component's method or property must not reuse a name of `HTMLElement` (`remove`, `title`,
  `hidden`…): it breaks the element. `make lint` (types and ESLint) catches it.
- Every setting has a description that says what it does and what it costs; the same text is in
  `translations/en.yaml` for the app's Configuration tab.
