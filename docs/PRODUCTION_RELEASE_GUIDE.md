# Production release guide

This guide is written for a first deployment. Complete staging before production. The product accepts synthetic cases and clinical case information that was properly de-identified before upload. It is not an autonomous diagnosis or treatment system.

## What will be deployed

- Vercel runs the private Next.js clinician interface and its authentication proxy.
- An OpenID Connect identity provider signs users in.
- Render runs the FastAPI service and verifies every access token independently.
- Render PostgreSQL stores case versions, decisions, evidence reviews, and audit packages by organization.
- Original uploaded files are processed transiently. They are not stored in the case-version database.

The browser never receives the Render service credential configuration. It calls the same-origin Next.js proxy, which forwards the authenticated request to FastAPI.

## Before using any real case

1. Obtain written approval from the organization responsible for the data.
2. Define which users and organizations are authorized.
3. Use an approved HIPAA de-identification process before upload. The product's identifier scan is only a secondary safeguard and is not a Safe Harbor or Expert Determination certification.
4. Confirm contracts, data-processing terms, retention, backups, monitoring, incident response, and regional hosting with every service provider.
5. Run security review, privacy review, local validation, and an observed staging pilot.

If the source might still contain protected health information, stop. Do not upload it.

## Step 1: Create the identity application

Use an organizational OpenID Connect provider such as Auth0, Okta, or Microsoft Entra ID. Create a regular web application and a protected API.

Record these values:

- issuer URL
- client ID
- client secret
- API audience

For staging, configure these URLs after Vercel gives you the staging domain:

- callback: `https://YOUR-STAGING-DOMAIN/api/auth/callback`
- logout return: `https://YOUR-STAGING-DOMAIN/`
- allowed web origin: `https://YOUR-STAGING-DOMAIN`

The access token must be a signed JWT. It must include `sub`, and should include `org_id` or an equivalent organization claim. If no organization claim is present, the backend creates a private personal organization boundary from `sub`.

## Step 2: Deploy the Render staging backend

1. In Render, choose **New > Blueprint**.
2. Connect this GitHub repository.
3. Select `render.yaml`.
4. Create the staging resources.
5. Enter every value marked as a secret or manual value.

Use these settings:

| Variable | Staging value |
|---|---|
| `OIDC_ISSUER` | Exact issuer URL, including `https://` |
| `OIDC_AUDIENCE` | Protected API identifier |
| `OIDC_ORGANIZATION_CLAIM` | `org_id`, or the provider's approved tenant claim |
| `CORS_ALLOWED_ORIGINS` | Exact Vercel staging origin |
| `TRUSTED_HOSTS` | Render API hostname only, with no scheme |
| `RATE_LIMITING_MODE` | Name of the configured shared edge or gateway limiter |
| `MONITORING_SINK` | Approved log and alert destination |
| `BACKUP_POLICY` | Approved backup policy identifier |
| `MODEL_AUTH_TOKEN` | Model provider secret |

Render creates PostgreSQL and supplies `DATABASE_URL` automatically. The database has no public IP allow list in the Blueprint.

After deployment, open `https://YOUR-RENDER-HOST/ready`. A ready service returns JSON with an `ok` status only when PostgreSQL is reachable. The detailed API documentation is disabled in production.

## Step 3: Deploy the Vercel staging frontend

1. In Vercel, import the same GitHub repository.
2. Set **Root Directory** to `web`.
3. Keep the detected Next.js build settings.
4. Add the following environment variables to the Preview environment.

| Variable | Value |
|---|---|
| `TUMOR_BOARD_API_URL` | Full Render API origin |
| `NEXT_PUBLIC_AUTH_MODE` | `oidc` |
| `OIDC_ISSUER` | Same issuer used by FastAPI |
| `OIDC_CLIENT_ID` | Web application client ID |
| `OIDC_CLIENT_SECRET` | Web application client secret |
| `OIDC_AUDIENCE` | Same API audience used by FastAPI |
| `APP_BASE_URL` | Exact Vercel staging origin |

Do not expose `OIDC_CLIENT_SECRET` as a `NEXT_PUBLIC_` variable.

## Step 4: Complete the staging checklist

Test with two separate users or organizations.

- Sign-in is required and sign-out clears the session.
- User A cannot list or open User B's cases.
- The guided synthetic AML case opens and completes the workflow.
- A clearly de-identified document can be processed after attestation.
- A document containing a test email, medical-record number, or full date is blocked before extraction.
- The original file is absent from PostgreSQL and application storage.
- Saving creates an immutable case version.
- Reopening the case restores the saved workflow, evidence review, human decision, and audit record.
- Logs contain request identifiers but no source document contents or access tokens.
- Backup restore has been tested into a separate staging database.
- Alerts and rate limits have been exercised.

## Step 5: Promote to production

Create a separate production environment with separate credentials and database. Repeat the full checklist. Protect the production branch and require CI checks before merge. Use a custom domain, update all callback URLs and trusted origins, then require organizational sign-off before enabling real de-identified cases.

## Stop conditions

Do not release real-case access if the product readiness screen reports a production blocker. Do not treat a green software readiness screen as clinical authorization. Institutional governance and accountable clinician review remain required.
