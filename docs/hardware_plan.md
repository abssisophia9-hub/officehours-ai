# Hardware Plan

## Kiosk Hardware Options
- **Option A**: Laptop or tablet running the kiosk web app in kiosk/fullscreen browser mode
- **Option B**: Raspberry Pi + touchscreen + USB NFC reader for a dedicated low-cost kiosk

## Check-in Methods
- **Barcode / QR scanner (MVP)**: Student scans the barcode/QR on their ID card with a USB scanner in HID keyboard mode. The scanner types the value into the kiosk check-in field and presses Enter, just like a keyboard.
- **Manual entry fallback**: Student or demo operator types the visible student ID (e.g. `117027`) into the same field. This exercises the same software path as a scanner.
- **NFC (future)**: Student taps a student ID card on an NFC reader connected to the kiosk. This may return a hidden card UID instead of the printed student ID, so it likely needs a mapping table.

## Components
| Component | Purpose | Notes |
|---|---|---|
| USB 1D/2D barcode scanner | Read printed student ID barcodes/QR codes | Recommended first hardware. Must support HID keyboard mode. |
| NFC reader (USB) | Read tap cards | Future path; confirm card compatibility before buying. |
| Kiosk display | Run the student-facing web app | Browser in kiosk mode |

## Privacy Note
Barcode/NFC check-in is used only to pre-fill identity for the kiosk session. Raw identifiers are not stored with the request unless the student chooses identified submission. See `docs/ethics_privacy.md`.
