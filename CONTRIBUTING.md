# Contributing to pulseengine.eu

## Prerequisites

- [Zola](https://www.getzola.org/) 0.22+ (`brew install zola`)
- Run `zola serve` from the repo root — site is at `http://localhost:1111`

## Project structure

```
content/          Markdown content (pages, blog posts)
templates/        Tera templates (layouts, shortcodes)
sass/             SCSS partials → compiled to main.css
static/           Static assets (JS, images, fonts)
```

## Writing blog posts

### Location

Create a new file in `content/blog/`:

```
content/blog/YYYY-MM-DD-slug-name.md
```

For posts with images, use a directory instead:

```
content/blog/YYYY-MM-DD-slug-name/
├── index.md
├── diagram.png
└── architecture.svg
```

Zola copies co-located assets to the output automatically.

### Frontmatter

```toml
+++
title = "Post Title"
description = "One-line summary — shown on listing cards and in <meta> tags."
date = 2026-03-05
[taxonomies]
tags = ["deep-dive", "meld"]
+++
```

- `date` controls sort order on the blog listing
- `description` is required — it appears on the blog index cards
- `tags` render as accent badges and generate tag pages at `/tags/<name>/`

### What you get automatically

| Feature | How |
|---|---|
| Table of contents | Generated from `##` and `###` headings — appears as a glass card above the post |
| Syntax highlighting | Fenced code blocks with language tag (`` ```rust ``). Theme: `material-theme-ocean` |
| Reading time | Automatic via Zola |
| Tags | Badge links to tag listing pages |
| Article width | 720px max, centered |

### Images

**Co-located (recommended for post-specific images):**

```markdown
![Fusion diagram](fusion-diagram.png)
```

Place the image file next to `index.md` in a post directory. Images get a glass border and rounded corners automatically.

**Shared images:**

Place in `static/img/` and reference as:

```markdown
![Diagram](/img/shared-diagram.png)
```

**Image captions:** Place italic text immediately after an image:

```markdown
![Architecture overview](architecture.png)
*Figure 1: The component fusion pipeline*
```

### Mermaid diagrams

Use the `mermaid` shortcode for inline diagrams. Mermaid JS loads only on pages that use it.

```markdown
{% mermaid() %}
graph LR
    A[.wasm] --> B[Meld]
    B --> C[Loom]
    C --> D[Synth]
    D --> E[Kiln]
{% end %}
```

The Mermaid theme is pre-configured to match the site's dark palette — no manual styling needed. The shortcode renders as `<pre class="mermaid">` to preserve newlines through Zola's HTML minification.

**Avoid HTML inside Mermaid node labels** — use plain text or Mermaid's native formatting. The content goes through Zola's markdown processor, so raw HTML tags get escaped.

For complex diagrams that don't change often, consider pre-rendering as SVG and including as an image instead (no client-side JS dependency).

### Callout notes

Use the `note` shortcode for callouts:

```markdown
{% note() %}
Default info-style callout.
{% end %}

{% note(kind="tip") %}
A tip with green accent.
{% end %}

{% note(kind="warning") %}
Warning with amber accent.
{% end %}

{% note(kind="danger") %}
Danger with red accent.
{% end %}
```

### Other shortcodes

| Shortcode | Purpose | Usage |
|---|---|---|
| `pipeline()` | Full pipeline SVG (Meld → Loom → Synth → Kiln + Sigil) | `{% pipeline() %}{% end %}` |
| `project_card(...)` | Glass card for a project | `{{ project_card(name="Meld", desc="...", url="...", icon="🔗", badge="accent") }}` |
| `mermaid()` | Mermaid diagram | See above |
| `note(kind="...")` | Callout box (info/tip/warning/danger) | See above |

### Content styling reference

These markdown elements are styled for the dark glassmorphism theme:

- `## H2` — top margin + subtle bottom border separator
- `### H3` — top margin, no border
- `> blockquote` — accent-blue left border, italic
- `` `inline code` `` — glass-surface background, mono font (Atkinson Hyperlegible Mono)
- Fenced code blocks — glass-surface background, syntax highlighted
- Tables — styled with hover highlights
- Lists — indented, dimmed text
- Links — subtle underline that brightens on hover

### Recommended post structure

```markdown
+++
title = "..."
description = "..."
date = YYYY-MM-DD
[taxonomies]
tags = ["..."]
+++

Opening paragraph — hook the reader, state what this post covers.

## First section

Body text with context.

![Diagram](co-located-image.png)
*Caption explaining the diagram*

## Implementation details

Code examples:

\```rust
fn example() -> Result<()> {
    // ...
}
\```

{% note(kind="tip") %}
Highlight important takeaways in callout boxes.
{% end %}

## What's next

Wrap up and point to related resources.
```

## Design system

### Colors (from thrum unified dashboard)

| Token | Value | Usage |
|---|---|---|
| `$bg` | `#0f1117` | Page background |
| `$surface` | `#1a1d27` | Card/panel backgrounds |
| `$surface-raised` | `#242836` | Elevated elements |
| `$border` | `#2e3345` | Borders |
| `$text` | `#e1e4ed` | Primary text |
| `$text-dim` | `#8b90a0` | Body text |
| `$text-faint` | `#5c6070` | Meta text, captions |
| `$accent` | `#6c8cff` | Links, highlights |
| `$green` | `#4ade80` | Success/verified |
| `$red` | `#f87171` | Error/danger |
| `$amber` | `#fbbf24` | Warning |
| `$cyan` | `#22d3ee` | Info/secondary accent |
| `$purple` | `#c084fc` | AI/MCP category |

### Badge variants

```html
<span class="badge badge--accent">Label</span>
<span class="badge badge--green">Label</span>
<span class="badge badge--amber">Label</span>
<span class="badge badge--cyan">Label</span>
<span class="badge badge--purple">Label</span>
<span class="badge badge--red">Label</span>
```

### Fonts

- **Sans:** Atkinson Hyperlegible Next (Google Fonts)
- **Mono:** Atkinson Hyperlegible Mono (Google Fonts)

## Deployment

Push to `main` triggers GitHub Actions:

1. `zola build`
2. SSH deploy to Netcup

Secrets required: `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_KEY`, `DEPLOY_PATH`

## Local development

```sh
zola serve          # http://localhost:1111 with live reload
zola build          # build to public/
zola check          # validate internal links
```
