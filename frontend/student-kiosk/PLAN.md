# Student Kiosk — Plan

> **Legacy shell** (`:5173`). Primary product UI is `frontend/officehours-app`
> (`:5180`). Shared-device web flow only — **no** barcode / NFC / kiosk hardware
> in scope.

## MVP built

- Manual student ID check-in (optional) or stay anonymous.
- Anonymous vs identified toggle on the request form.
- Free-text request submission form.
- Confirmation screen after successful backend submission.
- Backend integration with `POST /requests/`.

## Out of scope

- USB barcode / QR scanners
- NFC / tap-card readers
- Dedicated Raspberry Pi / physical kiosk builds
