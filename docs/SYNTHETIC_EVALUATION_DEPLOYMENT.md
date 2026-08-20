# Synthetic evaluation deployment

This is the first hosted evaluation profile. It demonstrates the complete governed product with the bundled synthetic AML case. It is not the production clinical deployment.

## Safety and product boundary

- Only the controlled synthetic AML teaching case is accepted.
- Patient and de-identified clinical document upload is disabled in the interface and API.
- No model-provider secret, identity provider, or production database is required.
- The site must be described as a synthetic faculty evaluation, not a clinical service.
- Do not enter patient information anywhere in the evaluation.

## What remains available

- source-linked case representation review
- governed evidence commissioning
- visible agent and workflow activity
- decision-support brief
- accountable human decision capture
- architecture and qualification console
- temporary case-version and evaluation history

## Important free-service limitation

Render's free web service uses an ephemeral filesystem and sleeps after inactivity. The first request after sleep can take about one minute. The temporary SQLite case history is lost after a restart, redeploy, or spin-down. This is acceptable for the synthetic evaluation only.

## Step 1: Deploy the Render API

1. In Render, choose **New > Blueprint**.
2. Connect `DataDrivenMed/cancer-tumor-board-intelligence`.
3. Use the default Blueprint path, `render.yaml`.
4. Confirm that the service is named `tumor-board-intelligence-synthetic-api` and the instance type is **Free**.
5. Deploy the Blueprint. No database should appear in the resource list.
6. Wait for the deploy to finish, then open the service URL followed by `/ready`.
7. A successful response includes `"status": "ok"`.

No Render secrets are required for this profile.

## Step 2: Deploy the Vercel interface

1. In Vercel, import the same GitHub repository.
2. Set **Root Directory** to `web`.
3. Keep the detected Next.js settings.
4. Add these environment variables:

| Variable | Value |
|---|---|
| `TUMOR_BOARD_API_URL` | The full Render service URL, without a trailing slash |
| `NEXT_PUBLIC_AUTH_MODE` | `none` |
| `NEXT_PUBLIC_DEPLOYMENT_PROFILE` | `synthetic_evaluation` |
| `APP_BASE_URL` | The final Vercel URL |

The same template is preserved in `web/.env.synthetic.example` for reference.

5. Deploy the Vercel project.

## Step 3: Verify the hosted evaluation

1. The home screen says **Synthetic faculty evaluation**.
2. Only **Open guided synthetic case** is available.
3. No patient-document upload option is visible.
4. Complete the representation review and evidence commissioning.
5. Run the governed workflow and confirm that backend events appear.
6. Record a human decision and inspect the audit panel.
7. Open the research console and review the detailed architecture.

## Later production path

The paid, identity-protected, PostgreSQL-backed configuration remains in `render.production.yaml`. Do not use that file until institutional hosting, identity, privacy, security, monitoring, backup, and governance requirements have been approved.
