# CLAUDE.md — Agent context for pulseengine.eu

## What this is

Static site for the PulseEngine org — landing page + blog at `pulseengine.eu`. Built with Zola (Rust SSG), glassmorphism dark theme, Mandelbrot fractal background.

## Key commands

```sh
zola serve          # Dev server at localhost:1111
zola build          # Build to public/
zola check          # Validate links
```

## Terminology — get this right

- PulseEngine is a **WebAssembly Component Model engine**, not a "toolchain" or "framework"
- Synth **transcodes** (not transpiles, not compiles) — it uses program synthesis
- Kiln is an **interpreter and runtime** (not just a runtime, not AOT)
- Everything is **work in progress** — do not make production-ready claims

## Project structure

- `content/blog/YYYY-MM-DD-slug.md` — blog posts (or directory with `index.md` for co-located images)
- `templates/` — Tera templates; `shortcodes/` for reusable components
- `sass/` — SCSS partials imported by `main.scss`; design tokens in `_variables.scss`
- `static/` — JS, images, fonts

## Writing blog posts

See `CONTRIBUTING.md` for the full guide including frontmatter, shortcodes, images, and Mermaid diagrams.

Quick reference:
- Frontmatter needs `title`, `description`, `date`, and `[taxonomies] tags`
- Use `{% mermaid() %}...{% end %}` for diagrams
- Use `{% note(kind="tip|warning|danger") %}...{% end %}` for callouts
- Co-locate images next to `index.md` in a post directory
- Syntax highlighting uses `material-theme-ocean`

## Design system

Colors are aligned with the thrum unified dashboard (`/Users/r/git/temper/thrum/crates/thrum-api/assets/style.css`). Key values:

- Background: `#0f1117`
- Surface: `#1a1d27`
- Accent: `#6c8cff`
- Text: `#e1e4ed` / `#8b90a0` (dim) / `#5c6070` (faint)
- Semantic: green `#4ade80`, red `#f87171`, amber `#fbbf24`, cyan `#22d3ee`, purple `#c084fc`

Fonts: Atkinson Hyperlegible Next (sans) + Mono, loaded from Google Fonts.

## Git workflow

- `main` is protected — always use PRs, never push directly
- CI runs `zola build` on PRs; deploy runs on push to `main` (tar + scp to Netcup)
- Commit messages: Conventional Commits (`feat:`, `fix:`, `docs:`, etc.)
- After merge, deploy takes ~20s — check with `gh run list --workflow=deploy.yml`

## Zola version notes

- Zola 0.22 uses `[markdown.highlighting]` (not `highlight_code`/`highlight_theme`)
- Theme names are from the Giallo library (e.g. `material-theme-ocean`, not `base16-ocean-dark`)
- Tera templates do not support array-of-arrays literals — use plain HTML for repeated elements
- Taxonomies use `[[taxonomies]]` (double bracket, TOML array-of-tables)
