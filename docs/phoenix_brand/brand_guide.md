# Phoenix Key Brand Guide

The Phoenix Key identity extends the BootForge visual language into a flagship symbol for recovery mastery. This guide captures the color system, logomark usage, and brand voice so the legendary feel remains consistent across documentation, UI surfaces, packaging, and marketing.

## 1. Core Logos

| Asset | Description | Recommended Use |
| --- | --- | --- |
| [`phoenix_key_badge.svg`](../../assets/logo/phoenix_key_badge.svg) | Circular phoenix crest with radiant circuitry and the neon key glyph. | Boot animations, USB imprint, splash screens, stickers. |
| [`phoenix_key_wordmark.svg`](../../assets/logo/phoenix_key_wordmark.svg) | Horizontal emblem with phoenix + key icon paired with the Phoenix Key tagline. | Landing pages, hero banners, presentation covers, product sleeves. |
| [`phoenix_key_monochrome.svg`](../../assets/logo/phoenix_key_monochrome.svg) | Simplified single-color mark for engravings or low-contrast media. | Laser etching, embossing, watermarks, single-color prints. |

Always provide at least 16px of padding around each logo and preserve aspect ratios. Use the SVG sources whenever possible to retain glow effects and vector fidelity.

## 2. Color Palette

| Role | Hex | Notes |
| --- | --- | --- |
| Phoenix Ember | `#FF6A2B` | Signature ring + flame gradient anchor, evokes molten energy. |
| Solar Apex | `#FF9C3F` | Highlights, flame shoulders, warm UI call-outs. |
| Aurora Neon | `#00F6FF` | Cyberpunk circuitry and key glow, use for accent strokes. |
| Deep Circuit | `#05090F` | Background plates, hero cards, dark mode surfaces. |
| Night Alloy | `#11171F` | Secondary text, monochrome mark fill, UI chrome. |
| Cloudsteel | `#F7F9FF` | Text on dark backgrounds, luminous edges. |

### Gradients

* **Ember Sweep:** `#FF3D1F → #FF6A2B → #FFBF4B`
* **Aurora Rise:** `#00F6FF → #0078FF`

These gradients appear in the badge core, CTA buttons, and neon outlines. Pair them with soft drop glows to retain the luminous identity.

## 3. Typography

* **Primary Display:** Orbitron SemiBold (or Eurostile / Bank Gothic fallback) — uppercase, wide tracking.
* **Body Copy:** Inter Medium for web content, Source Sans 3 for documentation.
* **Accent Script:** Use sparingly for signatures (e.g., "Bobby Blanco") with a handwritten brush font.

Maintain generous letter spacing (6–12 units) on headlines to emphasize futurism. Body copy should target 1.5 line height for readability.

## 4. Iconography & Motifs

* Circuit traces and diagnostic glyphs should use rounded line caps at 3–6px on 512px artboards.
* Glows should sit behind shapes with a blur radius between 3–6px.
* Incorporate key-cut silhouettes and phoenix feather curves to tie UI controls back to the brand.

## 5. Usage Guidance

1. **Legibility First:** When placing on bright backgrounds, switch to the monochrome mark or apply a 60% black overlay behind the badge.
2. **Scale Considerations:** Minimum display sizes — Badge: 96px, Wordmark: 320px width, Monochrome: 48px.
3. **Animation Cues:** Fade-in the badge from 0→100% opacity over 600ms with a 1px stroke glow ramp for boot animations.
4. **Physical Media:** For laser etching, convert gradients to single color (#11171F) and outline strokes.

## 6. Brand Voice

Phoenix Key copy should feel:

* **Legendary** — speak to mastery, resurrection, triumph.
* **Technical** — reference diagnostics, firmware, cross-platform prowess.
* **Assured** — confident but not arrogant; every promise is backed by engineering.
* **Encouraging** — invite users to "reignite" and "rebuild" with momentum.

## 7. Next Steps

* Render raster exports at 512×512 (badge) and 1920×1080 (wordmark hero) for distribution.
* Integrate the badge into the Phoenix Web GUI splash screen.
* Add brand-check automation to verify only approved palette values in UI themes.

By aligning on these standards, every Phoenix Key touchpoint will echo the Excalibur-grade story we are forging.
