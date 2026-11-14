# RouteIQ Design Spec

RouteIQ uses a quiet, premium product-page aesthetic: generous whitespace, precise typography, soft grouped surfaces, and restrained motion. The interface adapts across requester, approver, process-owner, analyst, and administrator roles without changing its visual language.

- Use the native Apple system font stack with Inter as the bundled fallback; never bundle SF fonts. Hero type is `clamp(44px, 7vw, 80px)` at 1.05 line height, with compact tracking. Body copy is 17px/1.47; captions are 13px and secondary.
- Define light and dark semantic tokens for page, surface, grouped surface, primary/secondary text, blue accent, semantic status colors, and subtle hairlines. Figures use tabular numerals; status pills use tinted backgrounds, not solid fills.
- Center content in a 1120px maximum-width frame with 12-column, 24px-gutter layouts. Desktop sections use 96–120px vertical rhythm; alternate page and grouped backgrounds.
- Cards use 28px radii, soft shadows, and restrained lift on hover. Buttons are pill-shaped. Navigation, sheets, and command surfaces use a 72%-opaque, blurred frosted treatment.
- Motion is calm and short, with shared-layout transitions and blur/fade reveals. Honor `prefers-reduced-motion` throughout. Charts use muted color, rounded shapes, and minimal gridlines.
- Dark mode is class-based, persisted, and follows system preference until the user chooses a theme. All pages, including the hidden design preview, use the same accessible tokens and primitives.
