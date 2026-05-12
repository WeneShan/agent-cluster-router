# Domain Docs

Single-context layout. All domain documentation lives at the repo root.

## Layout

| File | Purpose |
|------|---------|
| `CONTEXT.md` | Shared domain language — jargon glossary, module names, key concepts |
| `CONTEXT-MAP.md` | Optional — only if this becomes a monorepo (not currently) |
| `docs/adr/` | Architectural Decision Records — why decisions were made |

## Consumer rules

Skills that read domain docs (`improve-codebase-architecture`, `diagnose`, `tdd`, `grill-with-docs`):
- Read `CONTEXT.md` first to learn the project's shared language
- Search `docs/adr/` for relevant past decisions before proposing changes
- Update `CONTEXT.md` and create new ADRs when the domain model changes

## Current state

- `CONTEXT.md`: not yet created (will be populated by `grill-with-docs`)
- `docs/adr/`: not yet populated
