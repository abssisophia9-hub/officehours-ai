# Hardware Plan

## Kiosk Hardware Options
- **Option A**: Laptop or tablet running the kiosk web app in kiosk/fullscreen browser mode
- **Option B**: Raspberry Pi + touchscreen + USB NFC reader for a dedicated low-cost kiosk

## Check-in Methods
- **QR Code**: Student scans a QR code (e.g., from their student ID app) using the kiosk camera or their own phone, which opens the submission form pre-filled with an anonymized session token
- **NFC**: Student taps a student ID card on an NFC reader connected to the kiosk

## Components
| Component | Purpose | Notes |
|---|---|---|
| NFC reader (USB) | Read student ID cards | See `hardware/nfc-reader/` |
| QR scanner (camera or USB scanner) | Scan QR codes | See `hardware/qr-scanner/` |
| Kiosk display | Run the student-facing web app | Browser in kiosk mode |

## Privacy Note
NFC/QR check-in is used only to generate a session token; raw identifiers are not stored in request logs unless the student opts into identified submission. See `docs/ethics_privacy.md`.
