# Tambaya NG Design System

Direction: **"Civic Paper, Lagos Night"**. A government-grade information product should feel like a well-set official document that is alive, not a neon SaaS page. Nigerian identity comes from a deep ink green used as ink (not a flag block), a warm laterite/amber accent and warm neutrals. The default theme is white and green: pure white surfaces, ink-green type and controls, green-tinted secondary surfaces. The dark "Lagos Night" theme stays available behind the toggle.

Sources synthesised: ui-ux-pro-max skill (`--design-system` output: AI-Native UI + Accessible & Ethical for government audiences; stagger 300-450ms; no emoji icons; 4.5:1 contrast; reduced motion), Magic UI / 21st.dev component source (shimmer button, border beam, shine border, spotlight card, text-animate blur-in, dock, bento grid), Awwwards Oct 2026 SOTD run (two-colour palettes, mono all-caps section labels, numbered steps, restrained preloaders), Framer AI templates (pill badge over headline, three numbered steps, bento features, fade-up 24px / 600ms expo-out), Nigerian fintech identities (Paystack one green on near-black navy; Kuda one deep purple + documentary Lagos photography; Moniepoint one blue; Flutterwave warm orange; the pattern: one authoritative dark, one owned hue, one warm accent, lots of space, no gradient soup).

## Typography (verified glyph coverage)

Hausa boko needs Ɓɓ Ɗɗ Ƙƙ Ƴƴ; Yoruba/Igbo need ẹ ọ ṣ ị ụ ṅ with combining tone marks. Checked against font binaries:

- Full coverage: **Inter**, **Merriweather**, **Noto Sans Mono**, Onest, Noto Sans/Serif, Montserrat, Lato, Fira Sans, Unbounded, EB Garamond.
- Missing Hausa hooked letters (do not use): Geist, DM Sans, Space Grotesk, Instrument Serif, Manrope, Plus Jakarta Sans, Outfit, Figtree, Sora, Poppins, Fraunces, Playfair Display, JetBrains Mono.

Chosen: `Merriweather` (display, optical size axis) / `Inter` (UI and body, `cv11 ss01`) / `Noto Sans Mono` (labels, NIN digits, reference codes).

## Tokens

See `frontend/css/tokens.css`. Highlights:

- Green ink: `#06231B #0B3D2E #146C43 #1F9D5A #8FD6A8 #E3F4E9`
- Accent: laterite `#C8552A`, amber `#E8A33D`, tint `#FBEBD3`
- Warm neutrals: paper `#FBFAF7 #F3F1EB #E7E4DB`, stone `#8A8778 #55534A`, ink `#171714`
- Dark surfaces: `#0D1210 #121A16 #1B2620`
- Radii 6/10/14/20/28/pill. Shadows warm (never blue-grey).
- Easing: entrances `cubic-bezier(.16,1,.3,1)`; layout `cubic-bezier(.65,0,.35,1)`; durations 150/300/600/800ms; stagger 50ms words, 60ms cards.

## Effects used (one animated border on screen at a time)

| Effect | Where | Technique |
|---|---|---|
| Shimmer button | hero CTA | conic-gradient spark in a container-query box (Magic UI) |
| Border beam | composer while answer streams | `offset-path: rect()` + double mask (Magic UI) |
| Shine border | hero demo card | 300% radial gradient under XOR mask, 14s |
| Spotlight card | service cards | one pointermove listener on the grid writing `--x/--y` |
| Blur-in word reveal | hero headline, first assistant line | blur(10px) + 20px, 400ms, 50ms stagger |
| Aurora blobs + grain | hero background | blurred gradient blobs, SVG turbulence at 5% |
| Glass header / dock | sticky header, language switcher | `backdrop-filter: blur(12px) saturate(1.4)` |
| Typing dots + caret | chat | 1.4s dot bounce, step-end blink |
| Fade-up on scroll | landing sections | IntersectionObserver, 24px, 600ms |

## Accessibility rules applied (skill priority 1 and 2)

- Body 16px, line-height 1.55, text contrast 4.5:1 in both themes (checked).
- Visible 3px focus ring (`--green-500`) on every control; skip link.
- 44x44px minimum targets; cursor-pointer on clickables; disabled states dimmed and inert.
- `prefers-reduced-motion`: all decorative animation off, final states rendered.
- Icons: inline SVG (Lucide-style, 1.5px stroke), `aria-hidden` beside text, `aria-label` when alone.
- Responsive at 375 / 768 / 1024 / 1440; no horizontal scroll; composer sticky with progressive blur.
- Streaming: response text revealed progressively so no 10s spinner; typing indicator announced via `aria-live="polite"`.
