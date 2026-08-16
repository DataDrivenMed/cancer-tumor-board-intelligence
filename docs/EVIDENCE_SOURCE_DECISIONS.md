# Evidence Source Decisions

This file records the product-v1 evidence-source choices for the research deployment. It contains no credentials or licensed content.

## Molecular actionability

**Primary public source: CIViC.**

Rationale:
- open, expert-curated precision-oncology knowledgebase
- CC0 public-domain dedication for CIViC content
- public API and downloadable releases
- explicit disease, molecular profile, evidence type, evidence level, direction, significance, source, and therapy context
- compatible with the platform's provenance-first and fail-closed architecture

CIViC is used as an evidence discovery/interpretation source. Its presence does not bypass the platform's clinical-actionability gate.

**Optional secondary source: OncoKB.**

OncoKB may be configured later when the deployment has the appropriate OncoKB license and API token. It is not required for the public research configuration and must not be scraped or redistributed.

## Safety

**Primary public source: FDA Structured Product Labeling / openFDA drug labeling API.**

FDA label data are used only as source material for verified safety records. Automated retrieval alone does not establish a patient-specific contraindication or dosing decision. The platform preserves source identifiers, label sections, and verification state.

## Guidelines

**Primary governed source: institution-authorized NCCN guidance when permitted by the institution's NCCN license/access terms.**

No NCCN content is committed to this public repository. The application accepts an authorized deployment-time guideline package. Until such a package is provided and verified, the guideline channel remains fail-closed.

Public authoritative summaries such as NCI PDQ remain classified as authoritative evidence summaries, not formal NCCN guidelines.
