# Device Test Plan — 3D and 2D modes

**Purpose:** confirm on real student hardware what this container cannot measure. The container has no GPU, so 3D was measured only with software rendering (8–12 FPS). 2D measured 60 FPS.

**Status: NOT STARTED.** This needs people with physical devices. Record every result in the table at the end; the release gate requires it.

## Device matrix (minimum)
| # | Device class | OS / browser | Why |
|---|---|---|---|
| D1 | School Chromebook (Intel Celeron / MediaTek, 4 GB) | ChromeOS, Chrome | Most common low-end school device |
| D2 | Windows laptop, integrated graphics | Windows 11, Edge and Chrome | Typical teacher/student laptop |
| D3 | MacBook (Apple silicon) | macOS, Safari and Chrome | WebKit engine |
| D4 | iPad (9th gen or newer) | iPadOS, Safari | Touch and WebKit; common in schools |
| D5 | Android phone, mid-range (2021 or newer) | Android, Chrome | Students' own phones worldwide |
| D6 | Low-end Android phone (2 GB RAM) | Android, Chrome | Low-resource regions |
| D7 | Any of the above with a screen reader | NVDA (Windows), VoiceOver (macOS/iOS), TalkBack (Android) | Accessibility sign-off |

## Procedure per device (about 30 minutes)
1. Copy `dist/ByrdWay_Physics_I_Honors.html` to the device and open it from local storage, with no network. On iPad/Android, also open it from a web server, because some mobile browsers restrict `file://`.
2. **Load:** record the seconds from tap to dashboard.
3. **3D labs** (Settings → Graphics → High), labs 4, 7, 9, 10, 14, 16 and 17:
   - Press Run, watch for 10 s, and estimate smoothness: smooth, minor stutter, or unusable.
   - Rotate and zoom the camera by touch or mouse.
   - Confirm the scene is framed (the object is visible and not cut off).
   - Note any blank or black canvas, or a browser warning.
4. **2D mode** (Graphics → Low): repeat step 3 for the same labs. Measurements must equal the 3D run for the same settings.
5. **Medium graphics:** run Lab 9 and Lab 16.
6. **Lesson and engines:** open lessons 5.3, 12.6 and 17.6, answer one practice question, flip two flashcards, and run one Formula Lab solve.
7. **Languages:** switch to Arabic and check right-to-left layout and formulas. Switch to Chinese, Hindi and Bengali, and check for missing-glyph boxes (□), which mean the device lacks fonts.
8. **Storage:** complete one section, close the browser, reopen it, and confirm the progress is kept. Use Settings → Export progress and confirm a file downloads.
9. **Battery and heat (phones, D5–D6):** run Lab 9 in 3D for 5 minutes and note the device temperature and battery drop.
10. **Screen reader (D7):**
    - Navigate the dashboard → a lesson → a practice question → a lab.
    - Confirm that the headings, buttons, slider names and values, and the feedback messages are all announced.

## Pass criteria
- 3D: at least "minor stutter" on D2–D5. If D1/D6 are unusable in 3D, 2D must be smooth, and the app must recommend Low graphics on that device.
- 2D: smooth on every device.
- No blank canvas, crash or lost progress on any device.
- The screen reader completes the core path without dead ends.

## Results (to be filled in by testers)
| Device | Tester | Date | Load (s) | 3D labs | 2D labs | Languages | Storage | Screen reader | Issues |
|---|---|---|---|---|---|---|---|---|---|
| D1 | | | | | | | | | |
| D2 | | | | | | | | | |
| D3 | | | | | | | | | |
| D4 | | | | | | | | | |
| D5 | | | | | | | | | |
| D6 | | | | | | | | | |
| D7 | | | | | | | | | |
