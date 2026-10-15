# Jawa Performance Dashboard

Dashboard, rebuilt automatically from the Bike CPS LMS Google Sheets (JAWA tab) and the retail attribution sheet.
Everything private lives in encrypted release assets (`jawa-state`) and Actions secrets.

- Workflow: `.github/workflows/deploy.yml` (runs 10:00 and 16:00 IST, or run it by hand from the Actions tab).
- Build: `pipeline/build.py`. Lead months up to Apr'26 are frozen history; May'26 onward comes from Drive; retails are matched by enquiryId.
- Sign-in: email login + admin panel via the same access service as the TVS dashboard (pipeline/auth.js). Secrets: `JAWA_STATE_KEY` (decrypts the state assets), `JAWA_SOURCES` (sheet IDs).

## Hosting behind Cloudflare Access (real login)
1. Create a free Cloudflare account and activate Zero Trust (free plan).
2. Create an API token (Account: Cloudflare Pages Edit, Access: Apps and Policies Edit) and note the Account ID.
3. `gh secret set CLOUDFLARE_API_TOKEN` and `gh secret set CLOUDFLARE_ACCOUNT_ID` on this repo.
4. Run the "Cloudflare Access setup (one-time)" workflow with the allowed emails. Test the lock in a private window.
5. `gh variable set JAWA_AUTH --body off` (drops the built-in email sign-in), then run "Jawa Dashboard Refresh".
6. Turn off GitHub Pages: `gh api -X DELETE repos/<owner>/Jawa-Dashboard/pages`.
Approve more people later in Zero Trust > Access > Applications > Jawa Dashboard > Policies.
