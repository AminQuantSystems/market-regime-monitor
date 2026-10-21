# MEEM Toolkit Design System

**Version:** 1.0
**Status:** specified. Not implemented.
**Tokens:** `MEEM_DESIGN_TOKENS.json`
**Scope:** every MEEM finance and investment-technology product. Market Regime Monitor is the first product to use this version. The tokens are framework-neutral. They contain no finance formulas.

## Authority

When a visual decision conflicts, use this order:

1. MEEM production brand specification and master logo assets
2. Approved MEEM Technologies website concept
3. This design system
4. An individual product UI specification
5. Legacy project-specific visual decisions

For new work, the production brand pack wins over an older UI decision. Historical Git commits are not rewritten. Portfolio Risk X-Ray colours are not copied into new MEEM products.

## Identity

Corporate identity:

```text
MEEM TECHNOLOGIES
ENGINEERING INTELLIGENCE
```

The approved identity is the Arabic meem-inspired abstract mark, the deep-sapphire-to-black transition inside that mark, a thin Deep Sapphire divider, the widely tracked MEEM wordmark, the Sapphire TECHNOLOGIES descriptor, and the ENGINEERING INTELLIGENCE tagline.

## Locked corporate colours

These four tokens are permanent. Changing them requires explicit owner approval.

| Token | Hex | RGB |
|---|---|---|
| Deep Sapphire | `#052689` | 5, 38, 137 |
| Jet Black | `#0D0D0D` | 13, 13, 13 |
| White | `#FFFFFF` | 255, 255, 255 |
| Supporting Charcoal | `#6E6E6E` | 110, 110, 110 |

Deep Sapphire means MEEM: corporate branding, a primary action on a suitable light surface, structural brand emphasis, and a selected brand state. It does not mean bullish, positive performance, outperform, low risk, buy, or safe.

Brand colour communicates MEEM. Semantic colour communicates financial or system meaning. Sapphire is not overloaded with a finance meaning.

## One product family

Market Regime Monitor, Portfolio Risk X-Ray, Portfolio Rebalancing Engine, Market Data Control Engine, and later portfolio, risk, model-productionisation, and research tools share this system.

The permanent rule is: the same semantic meaning uses the same semantic colour. An application may change its layout. It may not invent its own green, red, amber, neutral, or information colour.

## Logo

Approved master assets:

- `MEEM_Primary_Logo_Master_Vector.svg`
- `MEEM_Standalone_Mark_Master.svg`

Approved convenience assets may include the transparent, reversed-white, black, and sapphire primary logos, and the gradient, black, sapphire, and white standalone marks.

The logo is placed from those assets. It is not recreated with CSS or typed letters. It is not stretched, skewed, rotated, recoloured, shadowed, glowed, stroked, respaced, or redrawn.

A compact analytical header uses the official standalone mark. The full logo is not squeezed into a small header.

Minimum widths:

- full logo with tagline: 240 px
- full logo without tagline: 140 px
- standalone mark: 24 px

Clear space around the full logo is at least about the cap height of the M in MEEM.

The authorised gradient lives only inside the approved logo asset. Application surfaces do not use gradients.

## Typography

Corporate direction is Montserrat, or the closest appropriately licensed geometric sans-serif. This phase does not download or package a font.

A future application stack may use:

```text
Montserrat, Inter, Segoe UI, Arial, sans-serif
```

Financial figures use tabular numerals where the font supports them. Reason codes may use a monospace face. The rest of the interface does not.

The character is geometric, precise, technical, restrained, premium, and institutional. It is not playful consumer software, oversized rounded cards, a crypto exchange, a neon terminal, aviation branding, or a gimmick dashboard.

| Role | Size | Weight |
|---|---|---|
| Product title | 20 px | 600 |
| Section heading | 16 px | 600 |
| Market name | 14 px | 600 |
| State label | 12–13 px | 600 |
| Secondary ticker | 11 px | 500 |
| Column heading | 10–11 px, uppercase, moderate tracking | 600 |
| Financial number | 12–13 px, tabular | 500 |
| Reason code | 10–11 px | 500 |

## Space and shape

Marketing uses space. Applications use density. Both use the same visual DNA.

The approved marketing site uses white space, Sapphire, Jet Black, technical linework, restrained geometry, and strong type. An application should feel like the professional software that site would show on a screen. It does not copy the homepage layout, the hero, the capability cards, or the website calls to action.

Application geometry:

- corner radius 2–4 px
- 1 px structural rules
- 2 px marker for a selected or active row
- precise rectangles
- compact controls
- a dense analytical layout

Avoid 12–24 px rounded cards, floating glass, surface gradients, glows, heavy shadows, neon, oversized metric cards, decorative 3D, and unnecessary motion.

Spacing uses a 4 px base: 4, 8, 12, 16, 24, 32, and 48 only where a major section actually needs it. The marketing site's large empty rhythm is not repeated inside the application.

Motion, when an interface is later built, lasts about 120–160 ms and covers hover, focus, row selection, and panel opening. There is no flashing, pulsing, continuous glow, moving background, or ticker animation. A reduced-motion preference is respected.

## Dark application surfaces

Market Regime Monitor V1 uses this dark analytical system. `#6D8CFF` is an accessibility colour for small interactive and informational content on very dark surfaces. It is not a replacement for corporate Sapphire `#052689`.

| Token | Hex |
|---|---|
| `dark.canvas` | `#0D0D0D` |
| `dark.surface_1` | `#111621` |
| `dark.surface_2` | `#161D2B` |
| `dark.surface_3` | `#1B2536` |
| `dark.border_subtle` | `#28354C` |
| `dark.border_interactive` | `#5B6E93` |
| `dark.text_primary` | `#F7F9FC` |
| `dark.text_secondary` | `#B9C1D0` |
| `dark.text_muted` | `#7F899B` |
| `dark.accent_accessible` | `#6D8CFF` |

## Light application surfaces

Specified for later MEEM tools, reports, and other suitable contexts. Theme switching is not implemented.

| Token | Hex |
|---|---|
| `light.canvas` | `#F7F8FC` |
| `light.surface_1` | `#FFFFFF` |
| `light.surface_2` | `#F0F3F8` |
| `light.border_subtle` | `#D8DEE9` |
| `light.border_interactive` | `#7A8799` |
| `light.text_primary` | `#0D0D0D` |
| `light.text_secondary` | `#4D5564` |
| `light.text_muted` | `#6E6E6E` |
| `light.accent` | `#052689` |

## Semantic colours

| Meaning | Dark surface | Light surface |
|---|---|---|
| Positive | `#2EA579` | `#1F6F55` |
| Negative | `#DE6672` | `#A73A48` |
| Attention | `#D49A2A` | `#8A5C00` |
| Neutral | `#8B95A5` | `#4D5564` |
| Information | `#6D8CFF` | `#2446A8` |
| Unavailable | `#7F899B` | `#5D6572` |
| System error | `#E36A75` | `#B42318` |

No further colours are added unless a later requirement is demonstrated. A negative market state is not a system error. System error is reserved for failed validation, invalid data, a failed operation, or an integrity failure.

## Accessibility

The target is WCAG 2.2 AA. Normal text is at least 4.5:1. Large text is at least 3:1 where that criterion applies. A meaningful boundary or graphic is at least 3:1. Colour is never the only carrier of meaning. Focus must be visible.

Contrast below uses the standard sRGB relative-luminance formula. No colour package was used. Ratios are rounded to two decimal places from the full calculation.

Text and brand pairs that meet 4.5:1:

| Foreground | Background | Ratio |
|---|---|---|
| `#FFFFFF` | `#052689` | 12.77 |
| `#F7F9FC` | `#0D0D0D` | 18.43 |
| `#F7F9FC` | `#111621` | 17.16 |
| `#F7F9FC` | `#161D2B` | 16.00 |
| `#B9C1D0` | `#0D0D0D` | 10.74 |
| `#B9C1D0` | `#111621` | 10.00 |
| `#7F899B` | `#161D2B` | 4.78 |
| `#7F899B` | `#111621` | 5.13 |
| `#7F899B` | `#0D0D0D` | 5.51 |
| `#6D8CFF` | `#161D2B` | 5.50 |
| `#6D8CFF` | `#111621` | 5.90 |
| `#6D8CFF` | `#1B2536` | 5.02 |
| `#6D8CFF` | `#0D0D0D` | 6.34 |
| `#2EA579` | `#161D2B` | 5.44 |
| `#DE6672` | `#161D2B` | 5.02 |
| `#D49A2A` | `#161D2B` | 6.79 |
| `#8B95A5` | `#161D2B` | 5.58 |
| `#E36A75` | `#161D2B` | 5.29 |
| `#0D0D0D` | `#FFFFFF` | 19.44 |
| `#4D5564` | `#FFFFFF` | 7.50 |
| `#6E6E6E` | `#FFFFFF` | 5.10 |
| `#052689` | `#FFFFFF` | 12.77 |
| `#1F6F55` | `#FFFFFF` | 6.06 |
| `#A73A48` | `#FFFFFF` | 6.28 |
| `#8A5C00` | `#FFFFFF` | 5.81 |
| `#2446A8` | `#FFFFFF` | 8.34 |
| `#5D6572` | `#FFFFFF` | 5.88 |
| `#B42318` | `#FFFFFF` | 6.57 |

The same dark semantic text colours also meet 4.5:1 on `#0D0D0D` and `#111621`.

### Adjustment

The proposed interactive border `#566A90` meets 3:1 on canvas (3.57), surface 1 (3.33), and surface 2 (3.10). On surface 3, `#1B2536`, it is 2.83:1. That fails the boundary role. It is not approved.

The approved token is `#5B6E93`. It is the smallest lightening of the proposal that reaches 3:1 on surface 3. Measured ratios: surface 3 is 3.00, surface 2 is 3.29, surface 1 is 3.53, and canvas is 3.79. The four locked corporate colours are unchanged.

### Roles that do not use a failing colour

`dark.border_subtle` `#28354C` is 1.58:1 on canvas and 1.47:1 on surface 1. It is a decorative hairline only. It does not indicate focus, selection, error, or a boundary the user must perceive. Those roles use `dark.border_interactive` or `dark.accent_accessible`.

Corporate Sapphire `#052689` is 1.52:1 on the dark canvas and lower on the darker surfaces. On the dark application it remains inside the official logo asset and in brand identity. A selected-row marker, keyboard focus, and other small meaning on a dark surface use `#6D8CFF`, which meets 4.5:1 as text and 3:1 as a marker. On light surfaces, Sapphire `#052689` is the accent and meets 12.77:1 on white.
