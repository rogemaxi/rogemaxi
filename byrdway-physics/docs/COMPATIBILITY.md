# Compatibility

## Tested
| Environment | Result | Evidence |
|---|---|---|
| Chromium (Playwright 1.56.1), Linux, WebGL via SwiftShader (software) | All browser suites pass: shell, lessons (170), labs (20 × 3D + 2D), engines, assessment, reference, accessibility, 12 languages | `docs/evidence/e2e-results.json` |
| Same, axe-core 4.10.2 WCAG 2.1 A/AA, 21 routes × English and Arabic | 0 violations | `docs/evidence/a11y-results.json` |
| Opened from disk (`file://`), no network | Works; no external requests at runtime except optional video links and an optional school tutor endpoint | E2E runs from `file://` |

## Not yet tested on real hardware
The following have **not** been tested in this build:
- Safari (macOS/iOS)
- Firefox
- Chromebooks
- Android tablets
- iPads
- screen readers (NVDA, JAWS, VoiceOver)

The build targets `es2020`, `chrome90`, `firefox88`, `safari14` and `edge90`. A school should run a short pilot on its own devices before rollout.

## Graphics
- **High** and **Medium** use WebGL through Three.js.
- **Low**, or any device without WebGL, uses the 2D canvas renderer automatically. The physics and measurements are identical in both, as the E2E checks confirm.
- The **Cinematic effects** toggle controls visual effects only. It is off when the operating system requests reduced motion.

## Fonts
The file embeds no fonts, to stay small. Chinese, Japanese, Korean, Hindi, Bengali and Arabic text uses the device's system fonts (font stacks in `src/styles.css`). Devices without those fonts may show missing-glyph boxes.

## Storage
Progress uses `localStorage`. If storage is blocked (some private modes or managed devices), the app keeps working in memory and shows a warning. **Settings → Export progress** saves a backup file.

## Narration
Read-aloud uses the device's built-in speech voices. When no voice exists for the selected language, the app says so and does not substitute a voice from another language.
