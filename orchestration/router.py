from __future__ import annotations

from schemas.agent import RoutingDecision
from schemas.case import CancerTumorBoardCase


ROUTER_VERSION = "1.0.0"
KNOWN_AGENTS = [
    "guideline",
    "molecular",
    "translational",
    "literature",
    "clinical_trials",
    "safety",
]


def _norm(value: object | None) -> str:
    return " ".join(str(value or "").strip().lower().replace("_", " ").split())


def _contains(text: str, *tokens: str) -> bool:
    return any(token in text for token in tokens)


def _question_domains(case: CancerTumorBoardCase) -> list[str]:
    text = f"{_norm(case.clinical_question.question_type)} {_norm(case.clinical_question.question)}"
    domains: list[str] = []

    if _contains(text, "treatment", "therapy", "management", "relapsed", "refractory", "salvage"):
        domains.append("management")
    if _contains(text, "molecular", "mutation", "variant", "genomic", "target", "biomarker"):
        domains.append("molecular_interpretation")
    if _contains(text, "mechanism", "biology", "pathway", "resistance", "translational", "preclinical"):
        domains.append("translational_biology")
    if _contains(text, "trial", "study", "eligibility", "experimental"):
        domains.append("clinical_trials")
    if _contains(text, "guideline", "standard", "recommended", "line of therapy", "standard of care"):
        domains.append("guideline_alignment")
    if _contains(text, "toxicity", "safety", "contraindication", "interaction", "dose", "tolerability"):
        domains.append("safety")
    if _contains(text, "evidence", "literature", "publication", "data", "study"):
        domains.append("literature")

    if not domains:
        domains.append("management")
    return sorted(set(domains))


def _complexity(case: CancerTumorBoardCase, domains: list[str]) -> tuple[str, list[str]]:
    score = 0
    reasons: list[str] = []

    if len(case.treatments) >= 3:
        score += 3
        reasons.append("Three or more represented treatment episodes")
    elif len(case.treatments) >= 1:
        score += 1

    if case.molecular_findings:
        score += 1
        reasons.append("Molecular findings require interpretation in clinical context")
    if len(case.molecular_findings) >= 3:
        score += 1
    if case.conflicts:
        score += 2
        reasons.append("Source conflicts remain represented in the case")
    if len(domains) >= 3:
        score += 2
        reasons.append("Clinical question spans multiple reasoning domains")
    elif len(domains) == 2:
        score += 1
    if case.transplant_cellular_therapy:
        score += 2
        reasons.append("Transplant or cellular-therapy history is represented")
    if case.toxicities:
        score += 1
        reasons.append("Prior toxicity history may constrain options")

    state = _norm(case.disease_state.value)
    if _contains(state, "relapsed", "refractory", "progressive", "progression"):
        score += 1
        reasons.append("Relapsed, refractory, or progressive disease state")

    if score >= 6:
        return "high_complexity", reasons
    if score >= 4:
        return "complex", reasons
    if score >= 2:
        return "intermediate", reasons
    return "routine", reasons


def route_case(case: CancerTumorBoardCase) -> RoutingDecision:
    """Deterministically route a pre-validated case to bounded specialist agents.

    Preconditions are enforced upstream by Semantic Integrity, Case Integrity / Data QA,
    and the Missing Information Agent. This router does not repair facts, infer missing
    information, retrieve evidence, or generate a clinical recommendation.
    """
    domains = _question_domains(case)
    selected: set[str] = set()
    required: set[str] = set()
    conditional: set[str] = set()
    rationale: list[str] = []
    warnings: list[str] = []

    # Safety is mandatory for every clinical tumor-board route.
    selected.add("safety")
    required.add("safety")
    rationale.append("Safety review is mandatory for every clinical route")

    if "management" in domains or "guideline_alignment" in domains:
        selected.add("guideline")
        required.add("guideline")
        rationale.append("Management or guideline-focused question requires guideline analysis")

    if "management" in domains or "literature" in domains or "guideline_alignment" in domains:
        selected.add("literature")
        required.add("literature")
        rationale.append("Current literature is required to contextualize management evidence")

    if "clinical_trials" in domains or "management" in domains:
        selected.add("clinical_trials")
        conditional.add("clinical_trials")
        rationale.append("Trial search is relevant to treatment-oriented tumor-board discussion")

    if case.molecular_findings or "molecular_interpretation" in domains:
        selected.add("molecular")
        required.add("molecular")
        rationale.append("Molecular findings or a molecular question require the Molecular Interpretation Agent")

    if "translational_biology" in domains:
        selected.add("translational")
        required.add("translational")
        rationale.append("Mechanistic or translational question explicitly requires the Translational Biology Agent")
    elif case.molecular_findings and ("management" in domains or "clinical_trials" in domains):
        selected.add("translational")
        conditional.add("translational")
        rationale.append("Translational analysis is conditionally relevant to molecular treatment context")

    # A pure safety question need not trigger unrelated evidence agents.
    if domains == ["safety"]:
        selected = {"safety"}
        required = {"safety"}
        conditional = set()
        rationale = ["Question is safety-specific; unrelated specialist agents are intentionally omitted"]

    complexity, complexity_reasons = _complexity(case, domains)
    rationale.extend(complexity_reasons)

    selected_ordered = [agent for agent in KNOWN_AGENTS if agent in selected]
    omitted = [agent for agent in KNOWN_AGENTS if agent not in selected]
    required_ordered = [agent for agent in KNOWN_AGENTS if agent in required]
    conditional_ordered = [agent for agent in KNOWN_AGENTS if agent in conditional and agent in selected]

    if not selected_ordered:
        warnings.append("No specialist route matched; safety review retained as fail-safe")
        selected_ordered = ["safety"]
        required_ordered = ["safety"]
        omitted = [agent for agent in KNOWN_AGENTS if agent != "safety"]

    return RoutingDecision(
        router_version=ROUTER_VERSION,
        question_type=case.clinical_question.question_type,
        question_domains=domains,
        complexity=complexity,
        selected_agents=selected_ordered,
        omitted_agents=omitted,
        required_agents=required_ordered,
        conditional_agents=conditional_ordered,
        rationale=rationale,
        routing_warnings=warnings,
        requires_parallel_execution=len(selected_ordered) > 1,
        requires_human_review=bool(case.conflicts),
        safe_to_execute=True,
    )
