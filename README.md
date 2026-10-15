# Jawa Performance Dashboard

Dashboard, rebuilt automatically from the Bike CPS LMS Google Sheets (JAWA tab) and the retail attribution sheet.
Everything private lives in encrypted release assets (`jawa-state`) and Actions secrets.

- Workflow: `.github/workflows/deploy.yml` (runs 10:00 and 16:00 IST, or run it by hand from the Actions tab).
- Build: `pipeline/build.py`. Lead months up to Apr'26 are frozen history; May'26 onward comes from Drive; retails are matched by enquiryId.
- Sign-in: email login + admin panel via the same access service as the TVS dashboard (pipeline/auth.js). Secrets: `JAWA_STATE_KEY` (decrypts the state assets), `JAWA_SOURCES` (sheet IDs).
