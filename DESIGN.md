# koala — design spec

Companion to `CLAUDE.md`. This covers the visual and interaction design;
`CLAUDE.md` covers the product, schema, and solver logic.

## Brand

App name is **koala**, always lowercase — wordmark, headers, everywhere,
even at the start of a sentence in UI copy. Do not capitalize it.

## Design philosophy

Calm and reassuring, confident and clear, simplistic. This is a tool for
a student under real academic stress — the UI should reduce anxiety, not
add to it. Every visual element should be grounded in something the
product actually does (the semester timeline, the conflict card, the
calendar grid) rather than generic decoration. No gratuitous animation,
no maximalism. When in doubt, remove an element rather than add one.

## Color tokens

| Token | Hex | Usage |
|---|---|---|
| `--koala-bg` | `#F4F5F1` | Page background, sage-tinted |
| `--koala-surface` | `#FFFFFF` | Cards, alternating section backgrounds |
| `--koala-ink` | `#202B2E` | Primary text |
| `--koala-muted` | `#5B6B66` | Secondary text |
| `--koala-muted-2` | `#8B968F` | De-emphasized text (e.g. second line of a two-line heading) |
| `--koala-border` | `#DDE1D9` | Hairlines, dividers |
| `--koala-primary` | `#1F5E56` | Primary actions, brand teal — the ONE dark accent color |
| `--koala-primary-tint` | `#BFD3CE` | Muted text/elements on top of `--koala-primary` |
| `--koala-gold` | `#C08A3E` | Warmth accent — used sparingly (graduation motif) |
| `--koala-attention` | `#B9704A` | Terracotta — flags, conflicts, "needs attention." NOT alarm-red. This is the one and only "something needs your attention" color across the app — reuse it, don't introduce a second warning color. |
| `--koala-success-bg` | `#E1F5EE` | Light success/complete fill |
| `--koala-success-text` | `#0F6E56` | Text on success fill |
| `--koala-attention-bg` | `#FAECE7` | Light attention/flag fill |
| `--koala-attention-text` | `#993C1D` | Text on attention fill |

**Rule: only ONE dark/saturated section per page at a time.** The landing
page's closing "join koala" band is the single deliberate dark-teal
accent. Everything else — including the pain-point/problem section — stays
in the light palette (white/sage alternating), using terracotta and gold
as accent colors rather than a colored section background. This was a
deliberate correction made during design: an earlier draft used a dark
teal band for the problem section and it read as inconsistent with the
rest of the page. Do not reintroduce a second dark section anywhere
without a specific reason.

## Typography

- **Display / headings**: Fraunces (serif, weight 500). Google Fonts:
  `family=Fraunces:opsz,wght@9..144,400;9..144,500`
- **Body / UI**: Work Sans (weight 400/500). Google Fonts:
  `family=Work+Sans:wght@400;500`
- **Numbers, dates, credit hours**: IBM Plex Mono (weight 500). Google
  Fonts: `family=IBM+Plex+Mono:wght@500`. Use this for anything precise —
  credit hour counts, dates, percentages — never for prose.

Two-line heading pattern (used in hero and the problem section): first
line in `--koala-ink`, second line in `--koala-muted-2` — de-emphasizes
the second clause without needing a smaller font size.

## Component patterns

- **Card** (`.pw-card` equivalent): white background, 12–14px radius,
  `box-shadow: 0 4px 16px rgba(32,43,46,0.06)`. No border needed when
  shadow is present against a sage/white background.
- **Pill/badge**: small rounded-pill label, 11–12px text, used for
  section eyebrows ("Features", "Reviews") and status tags ("Complete",
  "1 flagged", "Planned"). Status pills use the success/attention
  bg+text pairs above; neutral pills use white bg + `--koala-border`.
- **Primary button**: `--koala-primary` fill, `--koala-bg` text, 8px
  radius. One primary button per view (same restraint principle as most
  design systems — don't let multiple CTAs compete).
- **Ghost/secondary button**: transparent fill, `--koala-border` outline.
- **Dashed card**: used once, deliberately, for the "built for double
  majors" feature card — signals "flexible/configurable" versus the
  solid cards around it. Don't overuse dashed borders elsewhere.
- **Star rating**: two stacked text layers using the `★` character (not
  an icon font) — a gray background layer and a gold foreground layer
  clipped to `rating/5 * 100%` width. This is what allows a clean half-
  star render (e.g. 4.5) rather than rounding to a whole star.
- **Metric card**: muted 12px label above, 22px `mono` value below,
  white card. Used in groups of 3–4 (credit hours breakdown, degree %).
- **Semester outlook card**: compact card (~110px) showing term label,
  credit hours (`mono`), and a status pill. The current semester gets a
  visible border in `--koala-gold` and bolder terracotta label text
  rather than a different background — status is shown via
  border/pill/text color, not by changing the card's fill.
- **Calendar grid course block**: colored fill tied to category, not
  arbitrary — success-tint green for on-track major courses, attention-
  tint terracotta for flagged/locked courses (with a small lock icon
  when `is_locked = true`), purple tint reserved for a third category
  (e.g. gen-ed) to keep categories visually distinct without introducing
  more than 3 block colors on one grid.
- **Signature element — the semester timeline**: a horizontal line with
  small circular nodes per semester, teal-filled for completed, gold-
  ringed for current, outlined for future, terracotta label for flagged.
  This appears on the landing page hero AND the dashboard — it's the one
  recurring visual motif that should NOT be redesigned per-screen. Reuse
  the exact same component both places.

## Layout patterns

- **Section rhythm**: alternate sage (`--koala-bg`) and white
  (`--koala-surface`) sections down the page, with 0.5px border dividers
  between them. This creates visual rhythm without needing color
  changes. The single teal closing band breaks this rhythm deliberately,
  once, at the very end.
- **Hero flanking cards**: use a 3-column CSS grid (side columns fixed
  width, center column `1fr`), NOT absolute positioning. An earlier
  draft used absolutely-positioned floating cards and they overlapped
  the headline text unpredictably depending on text length. Grid layout
  guarantees no overlap regardless of content length — always prefer
  this over absolute positioning for any "flanking" layout.
- **Bento feature grid**: asymmetric grid (e.g. `1.3fr 1fr`), not a
  uniform 3-column list — mix card sizes/shapes (a stat ring, a dashed
  card, a wide card) to avoid the generic "3 equal feature boxes" look.
- **No internal page navigation.** This is a single scrolling landing
  page — no anchor/jump links between sections, no hamburger menu. Nav
  bar contains only the wordmark and Sign in / Get started. This was a
  deliberate simplification made during design — don't add nav links
  back in.

## Motion spec

Restrained and purposeful — nothing decorative:

- **Scroll reveals**: feature/testimonial cards fade + rise 12px over
  ~300ms as they enter viewport, staggered ~60ms per card in a row.
- **Buttons**: `scale(0.98)` on press, background lightens ~8% on hover,
  150ms ease.
- **Hero floating cards**: slow (~4s), barely-perceptible vertical float
  (±4px) — signals "alive" without being distracting.
- **Semester timeline**: nodes fill in left-to-right on first scroll
  into view — this animates real data (progress), not decoration.
- Nothing else animates. No parallax, no hover-tilt, no page-load
  choreography.

## Copy voice

- Sentence case everywhere — headings, buttons, labels. Never Title Case
  or ALL CAPS, including section eyebrows.
- Active voice, verb-first buttons: "Get started", "Create account",
  "Swap a course" — not "Submit" or "Click here".
- No exclamation points on system copy. No "simply/just/easy" (they
  presume and condescend). No "successfully" on confirmations — the
  confirmation itself is the success signal.
- Errors say what happened and what to do, in one sentence, no "Error:"
  prefix — e.g. "Removing this drops you to 9 credit hours, below the
  12-hour minimum — add a replacement first" (see `CLAUDE.md`'s
  credit-hour constraint section for when this fires).
- "Your" for the student's things ("Your schedule"), never "My".

## Screen inventory

Built and locked during design (see chat history for full mockups):

1. **Landing page** — nav (wordmark + sign in/get started only) → hero
   (flanking metric cards + two-line heading + timeline signature
   element) → problem section (white, terracotta-accented, real
   conflict-card visual) → features (bento grid) → reviews (star
   ratings, sample-labeled) → closing join band (the one dark-teal
   section) → footer.
2. **Auth** — single card, tab toggle between Sign in / Create account
   (not separate pages). Create account fields: first name, last name,
   school (disabled, pre-filled "Oral Roberts University" — do NOT make
   this a free-text or multi-school field), school email, password,
   confirm password. See `CLAUDE.md` for the `@oru.edu` enforcement
   requirement (client + server-side hook).
3. **Dashboard (main workpage)** — app header (wordmark + notification
   bell + avatar) → greeting + timeline (current semester enlarged/
   ringed) → 4 metric cards (credits completed/in-progress/remaining,
   degree %) → semester outlook row (horizontal scroll of compact cards)
   → expanded semester detail: weekly calendar grid with colored course
   blocks, lock icons on manually-overridden courses, and a caption
   explaining why a semester is flagged.

- **Search-then-chip pattern**: for any multi-select from a large list
  (majors, minors, and likely course search in onboarding step 3) — a
  search input filters a live results dropdown; selecting a result adds
  it as a solid teal chip above the search box, removable via an `×`.
  Do NOT render all options as always-visible chips — this was tried for
  program selection with ~41 real minors and was correctly identified as
  unusable at that scale. Auto-derived selections (e.g. a structurally-
  required minor added because of the student's major) get a visually
  distinct chip variant: outlined instead of filled, with an info icon
  and inline explanation, since it's not a normal removable choice in
  the same sense.

- **Course history two-state tag**: onboarding step 3 uses only two
  selectable tags per course — Done, In progress. "Not taken" is NOT a
  selectable option; it's the implicit default for any untouched course
  (and drives the dimming behavior). Clicking an already-active tag
  toggles it back off (returns to not-taken/dimmed) rather than
  requiring a separate "clear" action.
- **Live in-place filtering vs. search-then-add**: step 1's program
  search (empty list, search to find and add) and step 3's course
  search (full list always visible, search narrows what's shown) are
  different patterns — don't conflate them. Step 3's search filters the
  already-visible grouped list live as the student types (hide
  non-matching rows, collapse a category header entirely if nothing in
  it survives the filter) — it does NOT open a separate results
  dropdown. Category pills (All/Major/Minor/Christian coursework, etc.)
  combine with the text filter rather than replacing it.

## Known gaps — not yet designed

- **Credit-hour bound blocked state**: the UI for what happens when a
  student tries to drop below 12 or exceed 18 credits (see `CLAUDE.md`
  re-solve cascade section — this is a hard block, not a soft flag, and
  needs a clear inline message, not just a rejected action).
- **Course override modal**: triggered by clicking a calendar grid block
  or the "Swap a course" link — not yet mocked.
- **Onboarding flow screens**: program selection, class standing/term
  confirmation, and the course history done/in-progress/not-taken
  tagging UI (see `CLAUDE.md` onboarding flow) — not yet mocked visually,
  though the flow/logic is fully specified.
- **Tutorial overlay**: dismissible walkthrough for new users — not
  mocked.
