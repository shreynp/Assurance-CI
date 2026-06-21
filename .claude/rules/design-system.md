# Design System — Assurance CI

## Direction: Pharma Compliance Portal

Inspired by Veeva Vault, ICH regulatory portals, and clinical trial management systems. Sapphire authority blue on a crisp white canvas. Trustworthiness signals through contrast and hierarchy — data integrity over chrome. Every pixel earns its place in the audit trail.

---

## Color Palette (OKLCH source → hex for Streamlit)

| Token           | OKLCH                   | Hex       | Use |
|-----------------|-------------------------|-----------|-----|
| `--bg`          | oklch(99% 0.005 253)    | `#F8FAFF` | App background — white with cool blue cast |
| `--bg-card`     | oklch(100% 0 0)         | `#FFFFFF` | Cards, sidebar, expanders |
| `--bg-hover`    | oklch(97% 0.008 253)    | `#EFF3FB` | Hover states |
| `--border`      | oklch(90% 0.02 253)     | `#D8E2F0` | All borders |
| `--border-hi`   | oklch(70% 0.08 253)     | `#7BA3CC` | Focus / active borders |
| `--primary`     | oklch(38% 0.12 253)     | `#005BAB` | Corporate sapphire — links, chips, active |
| `--primary-bg`  | `--primary` at 8% alpha | —         | Badge/chip backgrounds |
| `--success`     | oklch(40% 0.14 155)     | `#137B4D` | PASS status |
| `--success-bg`  | `--success` at 8% alpha | —         | Pass badge backgrounds |
| `--danger`      | oklch(46% 0.19 27)      | `#C0392B` | FAIL status, errors |
| `--danger-bg`   | `--danger` at 8% alpha  | —         | Fail badge backgrounds |
| `--amber`       | oklch(58% 0.16 65)      | `#D4820A` | In-progress, warnings |
| `--amber-bg`    | `--amber` at 8% alpha   | —         | Pending badge backgrounds |
| `--text`        | oklch(20% 0.02 253)     | `#1A2333` | Primary body text |
| `--text-muted`  | oklch(55% 0.04 253)     | `#6B7D96` | Labels, metadata, secondary |

**Banned**: dark navy/black backgrounds, mint/green accents, purple gradients, flat gray #F5F5F5 backgrounds.

---

## Typography

| Role    | Family              | Weight | Size   | Notes |
|---------|---------------------|--------|--------|-------|
| Display | Plus Jakarta Sans   | 800    | 2rem   | Page titles, section headers |
| Heading | Plus Jakarta Sans   | 700    | 1.5rem / 1.1rem | H2/H3 |
| Body    | Plus Jakarta Sans   | 400/500/600 | 0.875rem | All prose, labels |
| Mono    | IBM Plex Mono       | 400/500 | 0.78–0.82rem | SHAs, paths, code, output |

**Banned fonts**: Inter, Roboto, Arial, system-ui as primary. Space Grotesk (overused). Syne (previous dark theme). JetBrains Mono.

Google Fonts import:
```
https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500&display=swap
```

---

## Spacing & Radius

| Token      | Value  | Use |
|------------|--------|-----|
| `--radius` | `8px`  | All cards, badges, chips |
| radius-sm  | `4px`  | SHA chips, inline code |
| radius-lg  | `12px` | Dialogs |

Spacing scale (multiples of 4px): 4, 8, 12, 16, 20, 24, 32, 48

---

## Shadow Recipe

```css
/* Card shadow — crisp, clinical */
0 1px 3px rgba(0, 91, 171, 0.06), 0 4px 16px rgba(0, 91, 171, 0.08)

/* Active card border glow */
0 0 0 2px rgba(0, 91, 171, 0.25), 0 4px 16px rgba(0, 91, 171, 0.12)
```

---

## Component Tokens

### Status Badges
```
PASS badge: bg rgba(19,123,77,0.08)    · text #137B4D · border rgba(19,123,77,0.25)
FAIL badge: bg rgba(192,57,43,0.08)    · text #C0392B · border rgba(192,57,43,0.25)
PENDING:    bg rgba(212,130,10,0.08)   · text #D4820A · border rgba(212,130,10,0.25)

Font: Plus Jakarta Sans 700, 0.7rem, uppercase, letter-spacing 0.05em
Shape: border-radius 20px, padding 3px 10px
```

### Story Chips (PROT-101 etc.)
```
font: IBM Plex Mono 500, 0.82rem
color: #005BAB · bg: rgba(0,91,171,0.08) · border: rgba(0,91,171,0.20)
padding: 2px 8px · border-radius: 4px
```

### SHA Chips
```
font: IBM Plex Mono 400, 0.78rem
color: #6B7D96 · bg: rgba(0,91,171,0.04) · border: #D8E2F0
padding: 2px 8px · border-radius: 4px
```

### Execution Output Block
```
font: IBM Plex Mono 400, 0.78rem, line-height 1.6
color: #1A2333 · bg: #F0F4FA
border: 1px solid #D8E2F0 · border-radius: 6px
padding: 0.875rem 1rem · max-height: 300px, overflow-y: auto
```

---

## Streamlit Theme (config.toml)
```toml
[theme]
primaryColor             = "#005BAB"
backgroundColor          = "#F8FAFF"
secondaryBackgroundColor = "#FFFFFF"
textColor                = "#1A2333"
font                     = "sans serif"
```

---

## Chart Palette (for matplotlib / plotly)
```python
CHART_PALETTE = [
    "#005BAB",  # sapphire — primary series
    "#137B4D",  # emerald — success / pass
    "#D4820A",  # amber   — tertiary / warning
    "#C0392B",  # crimson — danger / failure
    "#7BA3CC",  # steel   — quaternary
    "#6B7D96",  # muted   — grid lines, axes
]

# Background: #F8FAFF  |  Grid: #D8E2F0  |  Tick labels: #6B7D96
```

---

## Motion

One orchestrated page-load pattern: stagger metric cards in with 80ms delay each, then fade in the table at 200ms. Use CSS `animation: fadeUp 0.3s ease forwards`.

```css
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
```

---

## Backgrounds

Never flat default white or gray. Always layered with intent:
- App bg: `#F8FAFF` — near-white with cool blue cast
- Card bg: `#FFFFFF` + 1px border `#D8E2F0` + shadow
- Subtle texture option: `linear-gradient(135deg, #F8FAFF 0%, #EFF3FB 100%)`
- Section header accent: `border-bottom: 2px solid #005BAB`
