# DataGuard: Figma plan (Member 5, Lab 13)

Build the design in Figma first, then match the code to it. The running app in `src/webapp/` is a first version. After you design in Figma, change the colours and spacing in `src/webapp/static/style.css` so the two match.

## 1. Styles (create these first)

| Style | Name in Figma | Value |
|---|---|---|
| Colour | primary | #4338CA |
| Colour | primary-soft | #ECEAFD |
| Colour | background | #F6F7FB |
| Colour | surface | #FFFFFF |
| Colour | text | #16192C |
| Colour | muted | #5B6078 |
| Colour | error / error-soft | #B42318 / #FDECEA |
| Colour | warning / warning-soft | #9A5B00 / #FFF3DC |
| Colour | info / info-soft | #1D4ED8 / #E6EEFE |
| Colour | good | #15803D |
| Text | Heading 1 | 44 / bold |
| Text | Heading 2 | 18 / bold |
| Text | Body | 16 / regular |
| Text | Small | 13 / regular |
| Spacing | 4, 8, 16, 24, 40 | use these only |
| Corner | card 14, button 10, pill full | |

Make a dark-mode version of every colour style too.

## 2. Components (build once, reuse everywhere)

1. Button: primary and secondary, with default, hover, focus, loading states
2. Dropzone: empty, dragging over, file chosen
3. Severity chip: error, warning, note (always an icon plus a word, never colour alone)
4. Rule pill
5. Stat card: errors, warnings, notes
6. Score ring: good, ok, poor
7. Table row and table header
8. Banner: error, warning, info
9. Page header with logo and dark-mode button

## 3. Frames (one page each, desktop 1440 wide and mobile 390 wide)

1. Upload: empty
2. Upload: file chosen
3. Upload: checking (button shows "Checking...")
4. Report: with problems
5. Report: filtered to errors
6. Report: all clear
7. Error: file could not be read
8. Error: wrong file type or too big
9. Dark mode version of frames 1 and 4

## 4. User flows (draw as arrows between frames)

- Happy path: Upload, file chosen, checking, report, download problems
- Problem path: Upload, file chosen, checking, error page, try another file, Upload
- Clean path: Upload, file chosen, checking, all clear
- Use Member 4's personas and journey map to decide which path to test first.

## 5. Interactive prototype

In Prototype mode, connect the frames: dropzone click goes to "file chosen", "Check my file" goes to "checking" then "report" (use After delay, 1 second), filter chips go to the filtered frame, "Check another file" goes back to Upload. Share the prototype link as View only.

## 6. Hand-off (so the team can see it)

- Put the Figma link in `docs/ux/figma-link.txt`.
- Export key frames as PNG into `docs/ux/exports/`.
- Compare with Member 4's wireframes. Any difference should have a reason, which you can write in your report chapter.
