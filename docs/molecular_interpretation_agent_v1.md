# Molecular Interpretation Agent v1.0.0

## Purpose
Interpret represented molecular findings only against pre-verified, disease- and alteration-specific evidence records.

## Safety invariants
- No verified molecular evidence record -> no molecular actionability claim.
- Gene identity alone never establishes pathogenicity, sensitivity, resistance, eligibility, or clinical actionability.
- Disease context and alteration context must both match the evidence record when specified.
- Biological relevance is distinct from clinical actionability.
- Prognostic or diagnostic evidence must not be silently converted into a therapeutic claim.
- Synthetic evidence is blocked in production mode.
- The agent never mutates the canonical patient case.

## Inputs
- Frozen canonical `CancerTumorBoardCase`.
- Versioned `MolecularEvidenceStore` containing independently verified records.

## Outputs
Typed `MolecularReport` containing one `MolecularFindingInterpretation` per represented molecular finding, matched evidence IDs, evidence directions, actionability tier, therapy labels when explicitly present in verified evidence, resistance/diagnostic/prognostic signals, limitations, and a synthesis-eligibility flag.

## Explicit non-goals
Version 1 does not infer somatic versus germline status, pathogenicity, clonality, structural-variant equivalence, copy-number significance, regulatory indication, treatment eligibility, or mechanistic plausibility from model knowledge. Those require dedicated verified evidence and later specialist layers.

## Production behavior
The bundled production molecular store is intentionally empty. The agent therefore returns `source_unavailable` rather than inventing an interpretation until independently verified molecular evidence records are connected.
