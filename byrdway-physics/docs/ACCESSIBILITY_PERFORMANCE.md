# Accessibility and Performance

## Accessibility: what is verified

**Automated audit.** axe-core 4.10.2, WCAG 2.1 A/AA rule set, 21 routes in English and in Arabic (right-to-left): **0 violations** (`node tests/e2e/a11y.mjs`). The routes cover the cover page, dashboard, units, a unit, two lessons, two labs, the labs hub, the engines hub, Flashcards, Formula Lab, Tutor, Error Detective, the assessment center, the diagnostic, Level 4, standards, glossary, videos and settings.

**Keyboard-only E2E suite** (`accessibility: keyboard-only use`). It checks that:
- the first Tab reaches the "skip to content" link;
- the skip link moves focus to the main region without changing the page;
- in-app navigation moves focus to the new page;
- flashcards flip with Enter;
- quiz answers submit with Enter and the feedback stays visible;
- labs can be predicted and run from the keyboard;
- sliders move with the arrow keys;
- every lab control has an accessible name.

**Reduced motion.** The operating system's reduced-motion setting turns cinematic effects off by default. Settings can override this either way.

**Built-in options:**
- high-contrast mode
- text size from 85 % to 150 %
- 2D low-graphics mode
- Arabic right-to-left layout, with formulas isolated so they read left to right

### Defects found and fixed by these tests
1. The predict gate dimmed lesson text to 45 % opacity, which failed contrast. It now uses an outline and stays readable.
2. The flashcard hint and the tutor prompt box failed contrast or had no label.
3. Lab sliders had no accessible name, because their `<label>` bound to an `<output>` element instead.
4. The skip link changed the URL hash and so triggered the router.
5. Pressing Enter in a numeric quiz answer also activated the newly focused button and skipped the feedback.

## Accessibility: what is NOT verified
- No manual screen-reader test (NVDA, JAWS, VoiceOver, TalkBack) has been done yet.
- Automated tools find only part of WCAG problems.
- The 3D lab scene is a canvas. Its information is also given as text (live measurements, equations, data table), but the 3D view itself is not described to screen readers beyond its label.

## Performance (measured in this container: 4 CPU cores, no GPU)
| Measure | Result |
|---|---|
| File size | about 3.4 MB (single HTML; Three.js bundled; lesson content in all languages included) |
| First load to dashboard, from disk | ≈ 1.1 s (DOMContentLoaded ≈ 1.05 s) |
| JS heap after load | ≈ 14 MB |
| Open a lesson | ≈ 0.2 s |
| Lab frame rate, 2D renderer | 60 FPS (Labs 4, 9, 17) |
| Lab frame rate, 3D renderer | 8–12 FPS — **software rendering (SwiftShader), not a GPU.** Real devices with any integrated GPU will differ; this has not been measured on student hardware. |

The physics runs at a fixed time step that does not depend on frame rate, so slow devices show fewer frames but the same results. If 3D is slow on a device, Settings → Graphics → Low uses the 2D renderer.
