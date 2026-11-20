# MIRAGE — Design System

Dark "obsidian ops console" aesthetic. Everything must be legible on a projector
from 3+ meters: large type, high contrast, thin accents, no low-contrast grays on
black for anything semantic.

## Color Tokens

Defined in `apps/web/src/app/globals.css` (CSS vars) + `tailwind.config.ts`.

| Token             | Hex       | Usage                                          |
| ----------------- | --------- | ---------------------------------------------- |
| `--bg-obsidian`   | `#07080C` | App background                                 |
| `--bg-panel`      | `#0D0F16` | Panel/card surfaces                            |
| `--bg-elevated`   | `#141824` | Elevated surfaces, modals                      |
| `--line`          | `#232A3D` | Hairline borders (1px)                         |
| `--ink-primary`   | `#EDEFF5` | Primary text                                   |
| `--ink-secondary` | `#9AA3B8` | Secondary text — never below ~13px             |
| `--accent-cyan`   | `#37E0D8` | Lens A / compliance persona, links, focus ring |
| `--accent-violet` | `#8B7CF6` | Lens B / buyer persona                         |
| `--accent-crimson`| `#FF3B5C` | Lens C / injections, alerts, bounding boxes    |
| `--accent-amber`  | `#FFB224` | Warnings, sleeper drift                        |
| `--accent-green`  | `#2FD67A` | Verified clean, passed checks, EXACT_MATCH     |
| `--heatmap-glow`  | `#FF7A18` | Pixel-diff heatmap hot spots                   |

Severity → color: `CRITICAL`/`alert`/`error` → crimson; `HIGH`/warning/drift →
amber; `done`/verified → green; `running` → cyan (with pulse animation).

Persona → color: Lens A `compliance_desktop` → cyan; Lens B `social_mobile_buyer`
→ violet; Lens C injections → crimson. Keep this mapping consistent everywhere.

## Typography

Loaded in `app/layout.tsx` via `next/font/google`:

- **Inter** (`--font-sans`) — UI chrome, labels, body.
- **JetBrains Mono** (`--font-mono`) — hashes, URLs, payloads, latencies, endpoints.

Scale (projector-safe minimums): page title 28–32px · section headers 18–20px ·
body 14–15px · captions/meta 12–13px (mono) — never smaller for evidence data.

## Signature Components (visual spec)

1. **ThreeLensStage** — 3 equal columns labeled `LENS A · COMPLIANCE`,
   `LENS B · BUYER`, `LENS C · INJECTION X-RAY` with the persona accent colors.
   Reality-Gap gauge: radial 0–100, gray <30, amber 30–69, crimson ≥70.
2. **WipeSlider** — 1280×800 screenshots stacked; draggable vertical divider with
   grab handle; `HEATMAP` toggle chips overlaying `heatmap.png` at ~70% opacity.
   Divider: 2px white line + 36px circular handle.
3. **InjectionOverlay** — screenshot at natural aspect; bounding boxes:
   2px crimson stroke, 12% crimson fill, 1.6s pulse; selected box → right-side
   inspector card with channel chip + `matched_triggers` chips + raw payload mono.
4. **PaymentRailFork** — SVG: one source node → fork into `DECLARED RAIL` (cyan)
   and `HIJACKED RAIL` (crimson) terminating at different gateway nodes; animated
   dash-flow along paths; descriptor strings under each gateway.
5. **SleeperTimeline** — horizontal track, ticks at Day 1 / 30 / 60; knob scrubs
   days; intact ticks green, drifted ticks crimson with fracture icon.

## Projector Legibility Rules

- Minimum semantic text: 12px; hashes/addresses may wrap but not shrink below 12px.
- Status must be readable by **shape + text**, not color alone (icons + words).
- Heatmap/photo regions may be rich; surrounding chrome stays flat dark panels.
- Animations: subtle 150–300ms ease; the only looping animations are `running`
  pulse, injection box pulse, and SVG flow dashes. Nothing else loops on stage.
- Avoid full-white flashes (screenshots excepted) — projector bleed.
