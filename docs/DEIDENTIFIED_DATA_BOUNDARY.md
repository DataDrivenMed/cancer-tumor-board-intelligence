# De-identified clinical data boundary

## Allowed input

- controlled synthetic cases
- clinical source material de-identified under the submitting organization's approved process
- case identifiers created for this product that cannot be mapped back to a patient by product users

## Prohibited input

- names, initials, email addresses, phone or fax numbers
- medical-record, account, beneficiary, device, certificate, or Social Security numbers
- street addresses, URLs, IP addresses, biometrics, or full-face images
- exact dates connected to an individual, except a year when permitted by the approved method
- ages over 89 unless grouped as required by the approved method
- any free text that can reasonably identify the individual

## Product controls

1. The user must attest that de-identification occurred before upload.
2. FastAPI runs a deterministic secondary identifier screen before model extraction.
3. A finding blocks processing and returns only masked context.
4. Original upload bytes live only for the request and are not written to case storage.
5. Persisted records are scoped to the authenticated organization.
6. Every saved case version is immutable and records its creator and organization internally.
7. The synthetic teaching case remains available without clinical data.

## Important limitation

The screen is intentionally conservative but cannot prove that data is de-identified. It does not perform or certify the HIPAA Safe Harbor method or Expert Determination. The submitting organization remains responsible for the de-identification method, authorization, contractual controls, and re-identification risk management.

## Incident response

If a user believes identifiers were uploaded, stop processing the case, preserve only the minimum security audit information required by policy, notify the designated privacy and security contacts, and follow the organization's incident-response procedure. Do not copy the source into tickets, chat, or logs.
