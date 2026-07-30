# Hardware Setup Guide

## Barcode / QR Scanner MVP
1. Use a wired USB barcode scanner that supports HID keyboard mode.
2. Connect it to the kiosk device. It should appear as a keyboard and require no custom app integration.
3. Open any text input and scan a student ID barcode.
4. Confirm the scanner types a value such as `117027`, then sends Enter.
5. In the student kiosk, scan/type that value on the check-in screen.

Manual typing into the check-in field is the demo fallback and uses the same
software flow as a scanner.

## NFC Reader Future Prototype
1. Connect USB NFC reader to kiosk device.
2. Install reader drivers only if required by the device.
3. Test whether the card returns the printed student ID or a separate card UID.
4. If it returns a card UID, add a backend mapping from `card_uid` to `student_id`.

## Kiosk Display
- Run the student-kiosk web app in fullscreen/kiosk mode in Chrome:
  `chrome --kiosk http://localhost:5173`

> **Product note:** supervisor / FYP demos use the unified app at
> http://127.0.0.1:5180 (`./scripts/run_product.sh`). Port **5173** is the
> hardware kiosk shell only.
