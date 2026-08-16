# Evidence Source Implementation Plan

This deployment uses three distinct evidence channels with separate trust boundaries:

1. NCCN or other institution-authorized formal/consensus guideline evidence, supplied at deployment time and never committed to the public repository.
2. CIViC as the primary public molecular-actionability knowledge source, with optional OncoKB augmentation only when appropriately licensed.
3. FDA Structured Product Labeling / openFDA as the primary public safety-label source.

The implementation must preserve these invariants:

- Retrieval is not verification.
- A public molecular knowledgebase record does not automatically create a management recommendation.
- FDA label retrieval does not automatically create a patient-specific contraindication or dose decision.
- Licensed guideline text must not be redistributed through the public repository.
- Source version, access date, exact source locator, and verification state remain visible in structured evidence.
