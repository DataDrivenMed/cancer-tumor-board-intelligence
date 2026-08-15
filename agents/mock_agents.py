from __future__ import annotations

from agents.base import BaseAgent
from schemas.agent import AgentOutput, AgentStatus
from schemas.case import CancerTumorBoardCase


class GuidelineMockAgent(BaseAgent):
    agent_id = "guideline"

    def run(self, case: CancerTumorBoardCase) -> AgentOutput:
        return AgentOutput(
            agent_id=self.agent_id,
            status=AgentStatus.COMPLETED_WITH_LIMITATIONS,
            summary="Mock guideline analysis. No live guideline source is connected yet.",
            findings=[{"type": "placeholder", "message": "Current milestone validates workflow only; no standard-of-care conclusion is generated."}],
            warnings=["No guideline evidence connector configured."],
        )


class MolecularMockAgent(BaseAgent):
    agent_id = "molecular"

    def run(self, case: CancerTumorBoardCase) -> AgentOutput:
        findings = [{"gene": m.gene, "alteration_type": m.alteration_type, "interpretation": "Not interpreted in skeleton build."} for m in case.molecular_findings]
        return AgentOutput(
            agent_id=self.agent_id,
            summary="Molecular findings recognized; clinical interpretation intentionally disabled.",
            findings=findings,
            warnings=["Molecular knowledge-base connector not configured."],
        )


class TranslationalMockAgent(BaseAgent):
    agent_id = "translational"

    def run(self, case: CancerTumorBoardCase) -> AgentOutput:
        return AgentOutput(
            agent_id=self.agent_id,
            summary="Translational analysis placeholder.",
            warnings=["Preclinical/translational evidence retrieval is not active."],
        )


class LiteratureMockAgent(BaseAgent):
    agent_id = "literature"

    def run(self, case: CancerTumorBoardCase) -> AgentOutput:
        return AgentOutput(
            agent_id=self.agent_id,
            summary="Literature retrieval placeholder.",
            warnings=["PubMed connector not configured."],
        )


class TrialMockAgent(BaseAgent):
    agent_id = "clinical_trials"

    def run(self, case: CancerTumorBoardCase) -> AgentOutput:
        return AgentOutput(
            agent_id=self.agent_id,
            summary="Clinical trial matching placeholder.",
            warnings=["ClinicalTrials.gov connector not configured."],
        )


class SafetyMockAgent(BaseAgent):
    agent_id = "safety"

    def run(self, case: CancerTumorBoardCase) -> AgentOutput:
        risks = []
        if case.performance_status is None or case.performance_status.status.value != "confirmed":
            risks.append({"issue": "Performance status unavailable", "severity": "moderate"})
        return AgentOutput(
            agent_id=self.agent_id,
            summary="Safety placeholder based only on structural case completeness.",
            findings=risks,
            warnings=["No drug-label or interaction service configured."],
        )
