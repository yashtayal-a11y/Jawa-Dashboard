# Jawa Performance Dashboard

Password-protected dashboard, rebuilt automatically from the Bike CPS LMS Google Sheets (JAWA tab) and the retail attribution sheet.
The published page is ciphertext only (StaticCrypt). Everything private lives in encrypted release assets (`jawa-state`) and Actions secrets.

- Workflow: `.github/workflows/deploy.yml` (runs 10:00 and 16:00 IST, or run it by hand from the Actions tab).
- Build: `pipeline/build.py`. Lead months up to Apr'26 are frozen history; May'26 onward comes from Drive; retails are matched by enquiryId.
- Secrets: `JAWA_PASSWORD` (page password), `JAWA_STATE_KEY` (decrypts the state assets), `JAWA_SOURCES` (sheet IDs).
