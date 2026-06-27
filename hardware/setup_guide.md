# Hardware Setup Guide

## NFC Reader
1. Connect USB NFC reader to kiosk device
2. Install reader drivers (see `hardware/nfc-reader/README.md` once added)
3. Test read with provided test script

## QR Scanner
1. Either use kiosk device camera (no extra hardware) or a dedicated USB QR scanner
2. See `hardware/qr-scanner/README.md` once added

## Kiosk Display
- Run the student-kiosk web app in fullscreen/kiosk mode in Chrome:
  `chrome --kiosk http://localhost:5173`
