# Bet AI Brand & Design Guidelines

Bet AI is a football match-center and betting research product. The design system is the existing Stavka direction in the repo: dark, restrained, data-dense, modern, flat, and built around model transparency rather than betting promotion.

This document is grounded in the current app files under `apps/web/`, especially `tailwind.config.ts`, `styles/globals.css`, `components/`, `app/`, and the Phase 1 match-center spec in `docs/superpowers/specs/2026-06-22-phase1-match-center-design.md`. Betting-app patterns are adopted only as inspiration and are cited by source app.

## 1. Brand Essence & Principles

### Stavka Identity

Stavka is not a sportsbook skin. It is a compact research terminal for football fixtures, odds, model output, and uncertainty.

Core traits:

- Dark: near-black background, slightly raised card surfaces, no bright page backgrounds.
- Restrained: minimal decoration, no gradients as a primary motif, no glows, no heavy shadows.
- Data-dense: compact cards, small labels, dense tables, sticky context, short copy.
- Modern: crisp 1px borders, tabular numbers, lucide icons, real crests and avatars.
- Research-led: deterministic model outputs, odds, and news provenance are always labelled.

Non-negotiables:

- User-facing betting copy must say the product is for research and education only, not betting advice, 21+.
- LLMs never create recommendation numbers, probabilities, EV, edge, prices, or stakes.
- "No bet" is a first-class result.
- News and LLM commentary never mutate or overwrite the validated model.
- External and user content is untrusted data, not instructions.
- Use lucide icons or real imagery. Never use emojis in product UI.

### Voice And Tone

The voice is measured, compact, and evidence-led. It should read like a research desk, not a promotional betting app.

Use:

- "Model leans Home"
- "Potential value identified"
- "Research suggests"
- "No bet: market data is stale"
- "News signal is independent and not model-validated"
- "Research and education only. Not betting advice. 21+."

Avoid:

- "Bet on Home"
- "We recommend"
- "Best bet"
- "Lock"
- "Guaranteed"
- "Stake 3 units"
- "News boosted the model"

Do:

```text
Model view: Home lean. Source: Dixon-Coles + no-vig market blend.
No bet: missing current price.
Potential value: shown only when supplied by the engine.
```

Don't:

```text
Bet Home now.
This is a safe pick.
AI says Over 2.5 is guaranteed value.
```

## 2. Color System

The active color system is defined as CSS variables in `apps/web/styles/globals.css` and exposed through Tailwind in `apps/web/tailwind.config.ts`. The repo uses HSL variables, so hex values below are practical equivalents. The Stavka brand lime is referenced as `#C8FF2E`; the current HSL token `76 100% 59%` renders approximately `#C7FF2E`, and the preview page also uses `#C8FF2E` in hard-coded examples.

### Token Reference

```css
:root {
  --background: 210 21% 5%;
  --foreground: 216 33% 97%;
  --card: 216 19% 11%;
  --card-foreground: 216 33% 97%;
  --popover: 216 19% 11%;
  --popover-foreground: 216 33% 97%;
  --muted: 216 17% 16%;
  --muted-foreground: 218 11% 59%;
  --border: 0 0% 100% / 0.08;
  --primary: 76 100% 59%;
  --primary-foreground: 210 21% 5%;
  --primary-hover: 76 100% 64%;
  --ring: 0 0% 100% / 0.16;
  --accent: 216 15% 20%;
  --accent-foreground: 216 33% 97%;
  --destructive: 0 72% 58%;
  --destructive-foreground: 216 33% 97%;
  --positive: 142 62% 47%;
  --caution: 42 83% 58%;
  --value: 76 100% 59%;
  --danger: 0 72% 58%;
  --win: 142 62% 47%;
  --draw: 218 11% 59%;
  --loss: 0 72% 58%;
}
```

| Token | HSL | Hex / alpha | Semantic role | Usage rules |
|---|---:|---:|---|---|
| `background` | `210 21% 5%` | `#0A0D0F` | App canvas | Main page background and deep surfaces. Body currently uses direct `#0B0E11`. |
| `foreground` | `216 33% 97%` | `#F5F7FA` | Primary text | Headings, primary labels, key data. |
| `card` | `216 19% 11%` | `#171B21` | Panel surface | Section cards, right rail panels, tables, boards. |
| `card-foreground` | `216 33% 97%` | `#F5F7FA` | Text on cards | Default card text. |
| `popover` | `216 19% 11%` | `#171B21` | Overlay surface | Sheets, menus, popovers. |
| `popover-foreground` | `216 33% 97%` | `#F5F7FA` | Overlay text | Text inside overlays. |
| `muted` | `216 17% 16%` | `#222730` | Secondary fill | Table headers, inactive controls, empty states. |
| `muted-foreground` | `218 11% 59%` | `#8B93A2` | Metadata text | Counts, timestamps, captions, low-priority labels. |
| `border` | `0 0% 100% / 0.08` | `rgba(255,255,255,.08)` | Separator | 1px borders and dividers. Primary structure token. |
| `primary` | `76 100% 59%` | `#C7FF2E` / brand `#C8FF2E` | Lime accent | Active state, primary action, selected deterministic value. Use sparingly. |
| `primary-foreground` | `210 21% 5%` | `#0A0D0F` | Text on lime | Only on `primary`/`value` fills. |
| `primary-hover` | `76 100% 64%` | `#CEFF47` | Lime hover | Hover/pressed state for lime controls. |
| `ring` | `0 0% 100% / 0.16` | `rgba(255,255,255,.16)` | Focus and active ring | Keyboard focus, selected outline. |
| `accent` | `216 15% 20%` | `#2B313B` | Subtle selected fill | Secondary active controls, caution badge base in current badge component. |
| `accent-foreground` | `216 33% 97%` | `#F5F7FA` | Text on accent | Text on dark selected fills. |
| `destructive` | `0 72% 58%` | `#E14747` | Error/destructive | Errors, destructive actions, critical failures. |
| `destructive-foreground` | `216 33% 97%` | `#F5F7FA` | Text on destructive | Text on destructive surfaces. |
| `positive` | `142 62% 47%` | `#2EC264` | Positive system state | Confirmed success, favorable result, positive data movement. Not betting encouragement. |
| `caution` | `42 83% 58%` | `#EDB73B` | Warning | Stale, delayed, partial, suspended, rumour-heavy. |
| `value` | `76 100% 59%` | `#C7FF2E` / brand `#C8FF2E` | Engine value | Only when deterministic engine marks value. Same discipline as `primary`. |
| `danger` | `0 72% 58%` | `#E14747` | Risk/error alias | Errors, invalid states, negative movement. |
| `win` | `142 62% 47%` | `#2EC264` | Result win | W/D/L form, result zones, positive match outcomes. |
| `draw` | `218 11% 59%` | `#8B93A2` | Result draw | Draw state, neutral probability segment. |
| `loss` | `0 72% 58%` | `#E14747` | Result loss/live badge | Loss states, live badge red family, negative movement. |

### Chart Palette

Use the existing semantic chart colors before introducing new chart tokens:

- Home/win/positive: `primary` or `win`.
- Draw/neutral: `draw` / `muted-foreground`.
- Away/loss/risk: `loss` only when the semantic is result/risk, not away team identity by default.
- Model value/edge: `value`.
- Caution/stale/news uncertainty: `caution`.

For future xG, momentum, and probability charts, keep the palette limited and label every color in legends. Do not add generic neon blue, purple, or gradient palettes unless they become explicit tokens.

### Contrast And Legibility Rules

- Primary body text must use `foreground` or `card-foreground` on `background`/`card`.
- Metadata can use `muted-foreground`, but not below `text-[11px]` for legal or research disclaimers.
- Lime `primary` must always use `primary-foreground` text.
- Do not place `primary` text on `background` for long copy. Use it for labels, icons, and selected accents.
- Red and green cannot be the only indicator. Pair with labels, icons, arrows, or status text.
- Borders should remain visible at 1px. If a surface needs stronger separation, add spacing or a slightly different surface, not shadow.

Do:

- Use lime for active tab, selected model-backed value, primary CTA.
- Use amber for stale, suspended, rumour-heavy, or incomplete.
- Use red for error, destructive, loss, or odds shortening.

Don't:

- Put glows around lime elements.
- Use green to make a market feel desirable.
- Use red to shame a "No bet" outcome.
- Invent one-off colors inside components.

## 3. Typography

### Current Implementation Truth

The current app imports fonts in `apps/web/app/layout.tsx`:

- Body: `Barlow`, weights `400`, `500`, `600`, `700`, assigned to `--font-sans`.
- Display: `Barlow Condensed`, weights `500`, `600`, `700`, assigned to `--font-display`.

`tailwind.config.ts` maps:

```ts
fontFamily: {
  sans: ["var(--font-sans)"],
  display: ["var(--font-display)"],
}
```

The brief mentions Inter as the body face, but the real repo currently uses Barlow. Until the implementation changes, brand guidance should treat Barlow as current body and Barlow Condensed as display. If the product adopts Inter later, update `layout.tsx` and this document together.

The repo does not currently define a custom `fontSize` scale in Tailwind. It uses Tailwind defaults plus arbitrary sizes such as `text-[10px]`, `text-[11px]`, and `text-[9px]`. The scale below is the recommended Stavka product scale, not a current Tailwind extension.

### Recommended Type Scale

| Name | Size / line-height | Current utility equivalent | Use |
|---|---:|---|---|
| `2xs` | `10px / 12px` | `text-[10px]` | Status pills, tiny labels, compact nav metadata. |
| `xs` | `11-12px / 16px` | `text-[11px]`, `text-xs` | Section labels, timestamps, market subtitles, disclaimers. |
| `sm` | `14px / 20px` | `text-sm` | Default UI text, market labels, fixture rows. |
| `base` | `16px / 24px` | `text-base` | Longer explanatory copy, forms, body text where space allows. |
| `lg` | `18px / 24px` | `text-lg` | Page titles, league names, score context. |
| `xl` | `20px / 28px` | `text-xl` | Compact display headings and key metrics. |
| `2xl` | `24px / 32px` | `text-2xl` | Major match/card metrics, not dense panels. |
| `3xl` | `30px / 36px` | `text-3xl` | Score header, rare hero-level match state. |
| `4xl` | `36px / 40px` | `text-4xl` | Reserved for true first-viewport display moments. Use rarely. |

### Typography Rules

- Use `font-display` for brand mark, league names, score, card metrics, and compact headings.
- Use `font-sans` for all body, table, form, and chat copy.
- Numeric data should use tabular numbers. The body enables tabular numbers globally, and `.numeric` exists as a utility.
- Letter spacing must be `0` or positive uppercase tracking for micro-labels. Do not use negative tracking.
- Use weights intentionally: `400` body, `500` labels, `600` section headings, `700` key metrics.
- Legal copy and disclaimers must remain readable and persistent.

Do:

```tsx
<span className="numeric font-display text-lg font-semibold">2.14</span>
<h2 className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
  Fair win probability
</h2>
```

Don't:

```tsx
<p className="text-[9px] text-muted-foreground">Not betting advice</p>
<h3 className="-tracking-tight">Market view</h3>
```

## 4. Spacing, Radius, Elevation, Borders

### Radius

Current Tailwind radius extensions:

```ts
borderRadius: {
  lg: "8px",
  md: "6px",
  sm: "4px",
}
```

Use:

- `rounded-sm` / `4px`: badges, tiny pills, close controls.
- `rounded-md` / `6px`: buttons, inputs, odds chips, table controls.
- `rounded-lg` / `8px`: cards, panels, grouped sections, sheets.

Avoid `rounded-xl`, `rounded-2xl`, pill-heavy styling, and decorative bubbles unless a specific existing primitive requires it.

### Spacing

The app currently uses compact dashboard spacing:

- Shell: `px-4 py-4` on mobile, `md:px-5 md:py-4`.
- Cards: `p-3 sm:p-4`.
- Dense rows: `px-3 py-2` or `px-3 py-2.5`.
- Section stacks: `space-y-3` and `space-y-4`.
- Sticky rail gap: `gap-4`.

Guideline:

- Keep repeated items compact.
- Use spacing to create hierarchy before adding decoration.
- Avoid cards inside cards. Use rows, dividers, or full-width bands inside panels.
- Preserve minimum `320px` usability from `globals.css`.

### Elevation

No shadows as a default. No glows.

Use these hierarchy tools:

1. Surface: `background`, `card`, `muted/35`, `muted/45`.
2. Border: `border-border`.
3. Spacing: `gap-3`, `space-y-4`.
4. Type: uppercase labels, display metrics, muted metadata.

### Borders

- Default border is `border-border`.
- Stronger state borders can use `border-primary`, `border-loss/50`, `border-win/50`, or `border-amber-500/30` when semantic.
- Do not use borders as decorative neon frames.

## 5. Iconography & Imagery

### Icons

Use lucide icons consistently. Current examples include `MessageCircle`, `ListFilter`, `Newspaper`, `ShieldAlert`, `LineChart`, `Target`, `CalendarClock`, `Trophy`, `Shield`, `User`, and `ExternalLink`.

Rules:

- Default icon size in labels: `size-3` to `size-4`.
- Primary actions: `size-4`.
- Nav icons: `h-5 w-5` on mobile, `h-4 w-4` in sidebar.
- Icons are monochrome by default and inherit text color.
- Use color only for semantic state: `text-primary`, `text-muted-foreground`, `text-loss`, `text-caution`.
- Every icon-only button needs an accessible label and visible focus state.
- Do not use emojis.

### Crests, Avatars, And Bookmakers

Existing asset policy:

- `TeamCrest` loads API-Sports team crests and falls back to a circular bordered initials/Shield mark.
- `LeagueCrest` loads API-Sports league crests and falls back to a Trophy mark.
- `PlayerAvatar` loads API-Sports player photos and falls back to a User mark.
- `BookmakerIcon` loads local `/bookmakers/{slug}.svg` and falls back to a text chip.

Guidelines:

- Use real crests and avatars wherever available.
- Keep fallbacks compact, bordered, and non-decorative.
- Use empty `alt=""` for decorative crests next to visible team names; use `aria-label` on fallback symbols.
- Do not use generic football stock imagery in functional match pages.
- Product imagery should reveal the actual team, league, player, market, or model state.

## 6. Motion & Micro-Interactions

### Current Motion

Current repo facts:

- `globals.css` defines a `prefers-reduced-motion: reduce` rule that effectively disables transitions and animations.
- `Skeleton` uses Tailwind `animate-pulse`.
- `Loader2` uses `animate-spin` in chat/news loading states.
- `MarketsBoard` rotates the chevron with `transition-transform group-open:rotate-180`.
- `Button`, `FixtureRow`, `TipCard`, and other controls use `transition-colors`.

The current `tailwind.config.ts` does not define custom keyframes. The patterns below are the Stavka target set to add when needed.

### Target Keyframes And Timings

| Pattern | Status | Duration | Easing | Usage |
|---|---|---:|---|---|
| Skeleton shimmer | Add or keep pulse fallback | `1200-2000ms` | linear | Loading rows/cards. Use shape-matching skeletons. |
| Accordion open/close | Add if replacing native `details` | `180-220ms` | ease-out/in | Market group expand/collapse. |
| Slide-in sheet | Current via Radix behavior / target refine | `180-240ms` | ease-out | Mobile chat, market filters, market details. |
| Fade-in | Add only for data replacement | `120-180ms` | ease-out | New rows/cards after fetch. |
| Pulse dot | Add only for live state | `1000-1400ms` | ease-in-out | LIVE indicator, never value picks. |

### Odds Movement

Adopted from bet365, DraftKings, and Stake:

- Drift up / longer price: `positive` flash or thin left border, plus `ArrowUp`.
- Shorten / lower price: `danger` flash or thin left border, plus `ArrowDown`.
- Fade back over about `2s`.
- Flash only the changed odds cell, not the whole row.
- Include previous price in muted `2xs` text only if supplied by engine/provider data.
- Disable flashes under `prefers-reduced-motion`; keep arrows and labels.

Example state labels:

```text
2.14 up from 2.06
1.78 down from 1.84
Suspended
Locked
Stale 12m
```

### Locked, Suspended, And Optimistic States

- Locked: lock icon, muted foreground, disabled interaction, no pulse.
- Suspended: caution tone, explicit `Suspended` label, no primary fill.
- Stale: caution badge with timestamp or age.
- Optimistic feedback: pressed state or spinner for refresh/save-like actions, then settle to normal or show caution/error. Do not use betslip-style celebratory confirmation.

Do:

- Animate state changes briefly and functionally.
- Pair motion with text/icon semantics.
- Respect reduced-motion globally.

Don't:

- Pulse value badges.
- Use confetti, glow, shaking, urgency timers, or "act now" motion.
- Animate LLM commentary as if it is live model output.

## 7. Component Library

All components should use existing tokens and patterns from `apps/web/components/`. New primitives should be introduced only when they remove real duplication across markets, odds, badges, or layout.

### Cards And Section Cards

Current basis:

- `ui/card.tsx`
- `ui/section-card.tsx`
- Used by `RecCard`, `TipCard`, `MarketsBoard`, `NewsPanel`, `WinProbabilityBar`, widgets.

Anatomy:

```text
+------------------------------------------------+
| SECTION LABEL                         action   |
|------------------------------------------------|
| body: data rows, chart, copy, controls          |
+------------------------------------------------+
```

Variants:

| Variant | Treatment | Use |
|---|---|---|
| Default | `rounded-lg border border-border bg-card p-3 sm:p-4` | Panels, model cards, news/chat blocks. |
| Dense | `rounded-md` or `rounded-lg`, `p-2` to `p-3`, smaller labels | Market rows, article cards, facts, timeline rows. |
| Interactive | Default plus `transition-colors hover:border-primary/60` | Linked cards like `TipCard`. |
| Empty | Border/card with centered muted text | No markets, no news, no recommendations. |
| Warning | Caution/destructive border with muted body | Stale data, non-validated signal, unavailable service. |

States:

- Hover: only interactive cards shift border or muted background.
- Active: pressed state for route/action cards.
- Selected: lime only when representing a selected deterministic state.
- Disabled: muted text and no pointer events.
- Suspended: keep the panel visible with `Suspended`, `Stale`, or `Unavailable` copy.

Do not nest UI cards inside other cards. Inside a card, use rows and dividers.

### Odds Buttons And Chips

Current basis:

- `MarketsBoard` outcome chips.
- `OddsBoard` provider odds rows.
- `widgets/OddsRow`.

Anatomy:

```text
+------------------+
| Outcome label     |
| 2.14              |
| optional sublabel |
+------------------+
```

Variants:

- `default`: border, card/background fill, foreground odds.
- `best-odds`: currently `border-primary bg-primary text-primary-foreground`.
- `provider-chip`: bookmaker source, compact.
- `line-chip`: handicap/total line selector.
- `movement-up`: positive border/arrow/temporary flash.
- `movement-down`: danger border/arrow/temporary flash.
- `suspended`: muted/caution, disabled.

States:

| State | Visual |
|---|---|
| Default | `border-border bg-card text-foreground` |
| Hover | `hover:bg-muted/45` or subtle border shift |
| Active | pressed surface, no layout shift |
| Selected | `border-primary bg-primary text-primary-foreground` |
| Disabled | opacity, `-` for missing price |
| Suspended | lock/pause icon, `Suspended`, no click |

Usage rules:

- Odds chips may display engine/provider numbers, but never create them client-side.
- Use `.numeric` / tabular numbers.
- Best-price highlighting is not a recommendation unless explicitly backed by engine decision fields.

### Tier And Confidence Badges

Current basis:

- Generic `Badge` supports `neutral`, `positive`, `caution`, `danger`, `value`.
- News tier styles are currently local to `NewsPanel`.
- Confidence appears as numeric in `RecCard` and dots in `EdgeBar`.

Tier badge rules:

| Tier | Treatment | Meaning |
|---|---|---|
| `OFFICIAL_CLUB`, `OFFICIAL_LEAGUE` | emerald border/fill | Highest provenance, still independent from model. |
| `VERIFIED_JOURNALIST`, `ESTABLISHED_MEDIA` | neutral zinc/muted | Credible reporting. |
| `AGGREGATOR`, `FAN_COMMUNITY`, `RUMOUR` | amber border/fill | Lower confidence, rumour-heavy, caution. |
| Unknown | muted | Unclassified. |

Confidence rules:

- Engine confidence may display numeric only when supplied by engine output.
- LLM confidence must be qualitative: `High`, `Medium`, `Low`, or `Unavailable`.
- Prefer 3-level gauge or badge for AI commentary, not percentages.

### Status Badges

Current basis:

- `LiveBadge` supports `LIVE` and `HT`.
- `FixtureRow` renders `FT`, `NS`, `AET`, `PEN`, `PST`.

Variants:

| Status | Treatment |
|---|---|
| `LIVE` | red/loss family, optional pulse dot only if implemented accessibly. |
| `HT` | red/loss family, no urgency copy. |
| `FT`, `AET`, `PEN` | muted status pill. |
| `NS` | neutral scheduled pill. |
| `PST`, `SUSP` | caution or danger pill with explicit label. |

Recommendation: add a shared `MatchStatusBadge` so fixture rows, headers, and filters use the same treatment.

### Dense Tables

Current basis:

- `ui/table.tsx`
- `StandingsTable.tsx`

Adopted from Sofascore and FlashScore:

- Compact rows.
- Subtle alternating backgrounds at 2-3% opacity.
- Sticky first identity column on mobile horizontal scroll.
- Inline status indicators and form chips.
- Numeric cells use tabular numbers and display font sparingly.

States:

- Hover: `hover:bg-muted/45`.
- Selected: muted row or primary marker, never heavy fill for whole table.
- Disabled/stale: muted row plus explicit badge.
- Suspended: keep row visible, mark unavailable.

### Accordions

Current basis:

- Native `details` / `summary` in `MarketsBoard`.
- First two market groups open by default.

Adopted from bet365:

- Descriptive group names.
- Count below or beside the title.
- Chevron rotation.
- Main/Popular sections expanded by default.

Anatomy:

```text
+------------------------------------------------+
| Group name                              v       |
| 12 markets                                      |
+------------------------------------------------+
| Market title                                    |
| [Home 2.14] [Draw 3.10] [Away 3.40]             |
+------------------------------------------------+
```

### Segmented Controls

Current basis:

- `ui/tabs.tsx`
- `MatchTabs`
- `DateStrip`
- Provider chips in odds views.

Target variants:

- Major view tabs: `Overview`, `Stats`, `Timeline`.
- Odds format: `Decimal`, `Fractional`, `American` once preference support exists.
- Period: `FT`, `1H`, `2H` for stats where data supports it.
- Market filter: `All`, `Main`, `Goals`, `Handicap`.

States:

- Default: muted text.
- Hover: muted surface.
- Selected: `bg-primary text-primary-foreground`.
- Disabled: opacity and no pointer events.
- Suspended: disable unavailable segments, keep label visible.

### Sticky Side Panels

Current basis:

- `ChatPanel` uses `lg:sticky lg:top-24`.
- Match page right rail stacks `NewsPanel` and `ChatPanel`, sticky on desktop.

Adopted from bet365 and Betfair side panels:

- Desktop rail width: current `19rem` to `20rem`.
- Sticky below app header.
- Independent content scroll if needed.
- No nested decorative cards.

Bet AI-specific rule: this is not a betslip. It is research context: news provenance and fixture-grounded chat.

### Mobile Bottom Sheets

Current basis:

- `ui/sheet.tsx` wraps Radix dialog.
- `ChatPanel` opens full-height chat on mobile.

Target bottom-sheet behavior from DraftKings, Stake, and common betting apps:

- Snap points: peek `30-40%`, half `60-70%`, full `90-100dvh`.
- Visible drag handle.
- Sticky title/action row.
- Scroll body.
- Close button with accessible label.
- Use for chat, market filters, market details, news details.

States:

- Closed, opening, open at snap point, disabled trigger, unavailable content.
- Reduced motion must remove slide/drag animation.

### Bottom Navigation

Current basis:

- `BottomNav` has 4 items: Scores, Tips, Table, More.
- `SidebarNav` shares the same tab list on desktop.

Target 5-item thumb-zone pattern from DraftKings, Stake, and Betano:

| Slot | Label | Icon direction | Notes |
|---:|---|---|---|
| 1 | Scores | calendar/list | Primary home. |
| 2 | Tips | lightbulb/target | Research opportunities. |
| 3 | Markets or Search | search/list-filter | New market discovery or fixture search. |
| 4 | Table | list ordered | League standings. |
| 5 | More | menu | Research, settings, engine status, responsible gambling. |

Rules:

- Height should be at least `56px`; hit targets at least `44px`.
- Active state uses foreground or lime, but keep nav calm.
- Preserve league query param behavior.
- Update sidebar and mobile nav together.

## 8. Layout & Information Architecture

### Current Routes

Real app route tree:

- `/` - Scores page.
- `/match/[id]` - Match center.
- `/tips` - Recommendations feed.
- `/table` - Computed standings.
- `/more` - More hub.
- `/research` - Research tools.
- `/settings` - Settings.
- `/preview` - Design reference page.
- `/api/fixture-chat` and `/api/fixture-news` - Next proxy routes.

There is no `src/` directory and no `/fixtures/[id]` route in the current app.

### App Shell

Current shell:

- Centered app container: `max-w-2xl` mobile, `md:max-w-5xl`.
- Sticky top header with brand and league context.
- `EngineStatusBanner` below header.
- Mobile fixed bottom nav; desktop sidebar nav.
- Footer disclaimer: "Research and education only. Not betting advice. 21+."

Keep the shell utilitarian. Do not introduce a marketing hero as the first screen.

### Match Center

Desktop current layout:

```text
+---------------------------------------------------------------+
| sticky app header + league context                            |
+--------------------------------------------+------------------+
| match header                               | News signal      |
| fair win probability                       | Ask Bet AI       |
| recommendation / no bet                    | sticky rail      |
| markets board                              |                  |
| stats, form, H2H, facts, timeline          |                  |
+--------------------------------------------+------------------+
```

Guidelines:

- Preserve the two-column desktop layout: main column plus `19rem-20rem` sticky right rail.
- Main column order should put deterministic model/market context before broader match evidence.
- Right rail supports research with news and chat; it is not the source of recommendation truth.
- Desktop should not hide core match content behind tabs.

Mobile current layout:

```text
score header
tabs: Overview | Stats | Timeline
Overview: probability, recommendation, markets, form, H2H, facts
floating Ask Bet AI button -> sheet
bottom nav
```

Guidelines:

- Keep read-only match context at the top.
- Keep tabs compact and stable.
- Use bottom sheets for chat, filters, and deep market details.
- Keep primary actions and inputs in the bottom thumb zone.

### Markets Board Organization

Current behavior:

- `GET /data/fixtures/{id}/markets` powers grouped sportsbook markets.
- `MarketsBoard` renders `Bet options`, total market count, group accordions, and outcome chips.
- First two groups open by default.
- Outcome label appends line values, such as `Over 2.5`.
- Best odds in a market are highlighted.

Target additions, adopted by source app:

| Pattern | Source app | Bet AI adaptation |
|---|---|---|
| Descriptive accordion groups | bet365 | Keep group headers for Main, Goals, Handicap, Halves, Specials or engine-provided names. |
| Quick-link chips | bet365 | Add horizontal category chips with counts and anchors. |
| Market search | DraftKings | Add compact search by market/outcome name. |
| Category tabs/counts | DraftKings, Betano | Add `Popular`, `Main`, `Goals`, `Handicap` where data supports it. |
| Dense odds rows | Stake, Pinnacle | Keep minimal chrome and compact cells. |
| Line selectors | Betano | Use horizontal handicap/total line chips. |
| All-lines mode | Pinnacle | Desktop option for all totals/handicaps where useful. |
| Sticky market header | bet365 | Pin mini match context plus search/filter on long market pages. |

Market layout rules:

- 1X2: stable 3-column grid.
- Two-way: stable 2-column grid.
- Totals: line selector plus Over/Under cells.
- Handicap: line selector plus home/away cells.
- Player/special markets: compact wrap or table only if labels remain readable.
- Never synthesize missing markets or lines.

### Fixtures List

Current behavior:

- Scores page filters fixtures by active league query param.
- `ScoresClient` groups by kickoff date and defaults to latest date.
- `DateStrip` handles date selection.
- `FixtureRow` shows kickoff/status, teams with crests, score/date, and `Tip` badge only when the engine decision is `recommend`.

Guidelines:

- Keep fixture rows dense and row-linked.
- Use crests for recognition.
- Do not show a `Tip` badge for abstain/no-bet.
- Use live/status badges consistently.
- Adopt DraftKings/Stake compact fixture-card density, without sportsbook betslip language.

### League Page And Table

Current IA uses `/` as the league scores view and `/table` as standings, controlled by `?league=...`. Do not add a league route unless the information architecture grows beyond scores, tips, table, research, and settings.

Guidelines:

- Header must show active league and season via `LeagueSwitcher`.
- Scores show league crest, date strip, and grouped fixtures.
- Table uses `StandingsTable`, computed from finished fixtures.
- Keep the note: "Computed from results; excludes any official point deductions."
- Adopt Sofascore/FlashScore dense tables: sticky identity column on mobile, form chips, subtle zone markers.

## 9. AI Integration Design System

AI should be deeply integrated, but never visually or semantically confused with validated model output. This is the most important product boundary in the interface.

### AI Surface Taxonomy

| Surface | Source | Can show numbers? | Visual treatment |
|---|---|---:|---|
| Validated model | Deterministic engine | Yes, only supplied fields | Data-first card, model label, numeric rows, lime only for true engine value. |
| Provider odds | Odds provider / engine listing | Yes, supplied odds only | Market board/chips, provider labels, movement/stale states. |
| News signal | Engine news pipeline | Weight/confidence only as supplied | Cautionary card, tier badges, independent-signal disclaimer. |
| Bet AI commentary | LLM grounded in fixture payload | No generated recommendation numbers | Muted explanation card/chat, qualitative confidence only. |

### Proactive AI Insight Panel

Do not bury the model view in chat. Add a proactive insight panel near the top of match overview, after fair probability and before or beside the recommendation card.

Anatomy:

```text
+------------------------------------------------+
| VALIDATED MODEL                       source   |
| Model lean: Home                               |
| Potential value: Over 2.5                       |
| Confidence: Medium                             |
| [Why this lean? v]                              |
+------------------------------------------------+
| collapsed details:                              |
| 1. Engine model probability                     |
| 2. Market implied probability                   |
| 3. Engine edge / EV if supplied                 |
| 4. Data freshness and no-bet blockers           |
+------------------------------------------------+
```

Example copy, with numbers only when supplied by engine:

```text
Model lean: Home (58% model vs 52% market implied)
Potential value: Over 2.5 (+3.1% edge)
Source: Dixon-Coles 35% + no-vig market 65%
```

If exact numbers are not available from the engine, write:

```text
Model lean: unavailable
No model-backed bet: missing current market price
```

Design rules:

- Label deterministic output as `Validated model`.
- Show source attribution in the card header or directly below the claim.
- Add a collapsible `Why this lean?` reasoning chain.
- The chain may explain existing values, not calculate new ones.
- Keep `No bet` visible and normal.
- Do not use sparkle icons for deterministic model cards.

Adopted patterns:

- DraftKings/Stake compact insight cards.
- Pinnacle-style probability/value explainability.
- Explainable AI pattern for visible source attribution.

### Qualitative Confidence

AI commentary confidence is qualitative only:

- `High`: strong deterministic support or multiple reliable non-conflicting sources.
- `Medium`: useful but with uncertainty, mixed support, or older data.
- `Low`: weak, stale, conflicting, or rumour-heavy.
- `Unavailable`: missing or out of scope.

Do not show LLM confidence as `78%`. Percentages imply calibration. Engine confidence may display as numeric only when the field comes directly from engine output, and it must be labelled as engine/model confidence.

### News-Signal Panel

Current `NewsPanel` already establishes the right separation:

- Title: `News signal`.
- Prominent warning: research signal, not betting advice, not model-validated.
- Disclaimer fallback: "News-informed independent signal only; NOT walk-forward-validated; not betting advice."
- Team sections for home and away.
- Top signals as amber rows.
- Article cards with source tier, category, weight, title, summary, external link, and weight bar.
- Optional independent direction lean.

Required fields and visual rules:

| Data | Display |
|---|---|
| `source_tier` | Tier badge: official/verified/aggregator/rumour treatment. |
| `weight` | `W: 0.00`, monospaced. Do not call it probability. |
| `flagged` | Top-signal treatment, visually separate from article list. |
| `published_at` | Recency label in expanded/card rows. |
| `category` | Compact uppercase label. |
| `url` | External-link icon and safe external link behavior. |
| `disclaimer` | Always visible near panel top. |

Critical rule: news can inform a separate research view, but it never changes the Dixon-Coles/no-vig model display.

### Chat Patterns

Current chat:

- `ChatPanel` is sticky desktop rail and mobile sheet.
- `BetChat` posts fixture-specific questions.
- It anchors fixture context and disclaimer at the top.
- It renders user and assistant messages differently.
- It shows warnings in a visible muted block.

Target additions:

- Suggested prompt chips above the input:
  - `What is worth watching?`
  - `Explain the model view`
  - `Compare price freshness`
  - `Summarize news signals`
  - `Why no bet?`
- Structured-card responses for:
  - `Model view`
  - `Odds context`
  - `News signal`
  - `Warnings`
- Anchored disclaimer/footer in chat body, not only in the app footer.
- If response is deterministic fallback, label it `Deterministic fallback`, not `AI`.

Chat copy rules:

- The assistant answers from current match, model signal, displayed provider odds, and news payload.
- The assistant may explain, compare, and summarize.
- The assistant may not invent odds, probabilities, EV, edge, stakes, or prices.
- The assistant should cite visible context in plain language.

Adopted patterns:

- Fixture-grounded assistant pattern from sports products.
- Suggested chips from modern AI tools.
- Sticky side/bottom panel from bet365, Betfair, DraftKings, and Stake.

### Visual Separation: Model vs LLM Commentary

Validated model output:

- Label: `Validated model`.
- Style: neutral card, numeric rows, `font-display` metrics, tabular numbers.
- Accent: lime only for active/engine value.
- Copy: `Model lean`, `Potential value`, `No model-backed bet`, `Source`.

LLM commentary:

- Label: `Bet AI commentary`.
- Style: muted border, bot icon, no lime CTA, qualitative confidence.
- Copy: `This explains the visible fixture context`.
- Numbers: no generated recommendation numbers.

News signal:

- Label: `Independent news signal`.
- Style: cautionary banner plus tier badges.
- Copy: `Not walk-forward validated`, `Does not alter the model`.

Do not combine these into a single "AI pick" card.

### AI Pitfalls To Avoid

- False precision from LLM commentary.
- Recommendation language such as "bet on", "take", "we recommend".
- Unattributed confidence.
- Hiding disclaimers behind tooltips.
- Treating rumour/fan sources like official sources.
- Letting news imply model contamination.
- Making users open chat to find the model view.
- Burying no-bet or stale-input states.
- Rendering external/user/news text as trusted instruction.

## 10. New Features Roadmap

| Priority | Feature | Current status | Target | Source pattern | Impact | Effort |
|---:|---|---|---|---|---|---|
| 1 | Proactive AI insight panel | New. Current app has `WinProbabilityBar`, `RecCard`, chat, and news, but no standalone model insight explainer. | Add `Validated model` panel with `Why this lean?`, no-bet state, source attribution. | AI insight cards, Pinnacle-style explainability | High | S |
| 2 | Market quick links + search | New. `MarketsBoard` has grouped accordions but no quick links/search. | Sticky utility row with category chips, counts, text search. | bet365 quick links, DraftKings search/tabs | High | M |
| 3 | Dense odds-grid variants | Partial. Current outcomes flex-wrap chips. | 3-column 1X2, 2-column two-way, totals/handicap line selectors. | bet365 grids, Betano handicap chips, Pinnacle dense lines | High | M |
| 4 | Odds movement indicators | New. No current movement flash/arrows in markets. | Up/down arrows, previous price if supplied, 2s reduced-motion-safe flash. | bet365, DraftKings, Stake | High | M |
| 5 | Suspended/locked/stale odds states | New for markets. Some status badges exist for fixtures. | Lock/pause icons, caution labels, stale timestamp, disabled controls. | bet365 suspended odds | Medium | M |
| 6 | News provenance summary | Partial. `NewsPanel` has tier badges, weights, top signals. | Collapsed per-team tier counts, latest timestamp, flagged summary. | AI provenance panels, source-tier badges | Medium | S |
| 7 | Mobile market bottom sheets | Partial. Chat uses full-height sheet. | Snap-point sheets for market filters and market details. | DraftKings, Stake, universal betting sheets | Medium | M |
| 8 | 5-item bottom navigation | Partial. Current bottom nav has 4 items. | Scores, Tips, Search/Markets, Table, More. Maintain league param. | DraftKings, Stake, Betano | Medium | S |
| 9 | Probability and edge bars | Partial. `WinProbabilityBar` and `EdgeBar` exist. | Standardize bars for model-vs-market, edge, and no-bet blockers. | Pinnacle-inspired value tools | Medium | M |
| 10 | xG and momentum visualization | New. Current stats are bars/timeline, no xG/momentum. | Add only when engine data exists; never fake xG. | Sofascore xG timeline/momentum | Medium | L |
| 11 | Mini league-table context | New on match page. Full `/table` exists. | 3-5 row table around both teams in match overview. | FlashScore table snippets | Medium | M |
| 12 | Odds format toggle | New. Current display is decimal-first. | Decimal/Fractional/American setting, applied consistently. | Stake odds format control | Low | M |
| 13 | Value badges refinement | Partial. `RecCard`, `TipCard`, `Badge` use value badges. | Unify value badge language and ensure it appears only for engine-backed value. | Pinnacle value indicators | Medium | S |

## 11. Accessibility & Responsive

### Breakpoints

The repo does not define custom screens in `tailwind.config.ts`, so Tailwind defaults apply:

| Breakpoint | Width | Current app role |
|---|---:|---|
| `sm` | `640px` | Slightly larger card padding, responsive grids. |
| `md` | `768px` | Desktop sidebar replaces bottom nav, shell widens. |
| `lg` | `1024px` | Match page becomes two-column with sticky right rail. |
| `xl` | `1280px` | Match right rail expands from `19rem` to `20rem`. |
| `2xl` | `1536px` | Available by Tailwind default; do not over-widen content by default. |

### Responsive Rules

- Build mobile first.
- Keep `html` usable at `320px`.
- Use truncation for team names, league names, bookmaker names, and long market labels.
- Use stable grid tracks for odds, tables, and nav so labels do not resize layouts.
- Hide low-priority table columns on mobile, but keep identity, status, and key numbers.
- Keep bottom nav and chat input outside content overlap.
- Never hide the research disclaimer completely.

### Focus States

Current `Button` primitive uses:

```tsx
focus-visible:outline focus-visible:outline-1 focus-visible:outline-offset-2 focus-visible:outline-muted-foreground
```

Apply the same standard to:

- Bottom nav links.
- Sidebar nav links.
- Date strip buttons.
- Market accordion summaries.
- Market outcome controls if interactive.
- Tabs and segmented controls.
- Sheet close buttons.
- Search/filter inputs.

For lime surfaces, use a dark/inset focus ring with sufficient contrast.

### Hit Targets

- Minimum mobile target: `44px x 44px`.
- Bottom nav height: `56-64px`.
- Icon-only buttons: at least `h-11 w-11` on mobile or equivalent padding.
- Odds chips: at least `44px` tall when selectable; read-only dense chips can be smaller if not interactive.
- Date strip buttons should use `min-h-11` on mobile.

### Motion Accessibility

- Respect existing `prefers-reduced-motion` rule.
- Do not rely on animation alone for status.
- Odds movement must also include arrow/text state.
- Loading must include readable text or skeleton shape, not just spinner motion.
- Live pulse must be optional and paired with `LIVE`.

### Color Accessibility

- Never use green/red alone.
- Pair every value/danger state with label, icon, or directional arrow.
- Keep amber caution readable on dark backgrounds.
- Do not put long lime text on dark backgrounds.
- Ensure disabled states remain legible enough to explain why unavailable.

### Content Safety

- Legal/research disclaimers remain readable and persistent.
- "No bet" is never hidden in an empty state.
- Stale/missing data explains the blocker.
- LLM commentary remains visually distinct from validated model output.
- External links use explicit external-link affordance.
