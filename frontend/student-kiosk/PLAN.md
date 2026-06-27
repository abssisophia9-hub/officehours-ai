# Student Kiosk — Plan

## MVP built

- Barcode/manual check-in screen for student ID capture.
- Anonymous vs identified toggle.
- Free-text request submission form.
- Confirmation screen after successful backend submission.
- Backend integration with `POST /requests/`.

## Hardware notes

- The check-in input works with USB barcode scanners in HID keyboard mode.
- Manual ID typing is the no-hardware demo fallback and uses the same software path.
- NFC/tap-card support is deferred until the card technology and scanned payload are confirmed.

## Next steps

- Test with a real student ID barcode scanner when hardware is available.
- Add NFC/card UID mapping only if tap cards return a different identifier than the printed student ID.
- Show estimated response path once professor recommendation cards are richer.
