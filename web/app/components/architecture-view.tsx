"use client";

import { useState } from "react";

type ArchitectureNode = {
  id: string;
  label: string;
  kind: "human" | "control" | "agent" | "evidence" | "output";
  role: string;
  input: string;
  output: string;
  guardrail: string;
  aiContribution: string;
};

const nodes: ArchitectureNode[] = [
  { id: "sources", label: "Clinical source packet", kind: "human", role: "Receives synthetic or fully de-identified pathology, notes, laboratory results, and structured case data.", input: "Clinician-supplied source material", output: "Bounded source segments with document identity", guardrail: "No source means no patient fact.", aiContribution: "AI can organize heterogeneous records while preserving the origin of every represented statement." },
  { id: "extraction", label: "Provenance-aware extraction", kind: "agent", role: "Structures represented facts without treating model memory as a patient-data source.", input: "Bounded source segments", output: "Candidate facts plus exact provenance anchors", guardrail: "Unsupported content cannot enter canonical patient state.", aiContribution: "AI accelerates record abstraction and normalization while deterministic checks preserve traceability." },
  { id: "canonical", label: "Canonical cancer case", kind: "control", role: "Provides one typed patient-state contract for every downstream service and agent.", input: "Reviewed extracted facts", output: "CancerTumorBoardCase schema", guardrail: "Unknown, pending, conflicting, and unavailable remain distinct states.", aiContribution: "A common schema lets multiple specialized agents collaborate without redefining the patient differently." },
  { id: "confirmation", label: "Clinician confirmation", kind: "human", role: "Confirms the represented patient state and the exact tumor-board question before routing.", input: "Canonical case and proposed question", output: "Human-confirmed representation", guardrail: "AI proposes; the clinician confirms or corrects.", aiContribution: "AI reduces preparation burden while keeping authority with the clinician." },
  { id: "semantic", label: "Semantic integrity", kind: "control", role: "Detects unsafe contradictions between structured fields and represented extraction state.", input: "Canonical case and raw extraction", output: "Pass or structured blocking findings", guardrail: "Failure stops all specialist propagation.", aiContribution: "Deterministic validation prevents polished downstream output from masking a corrupted representation." },
  { id: "integrity", label: "Case Integrity / Data QA", kind: "control", role: "Checks provenance, diagnostic coherence, treatment identity, chronology, and schema consistency.", input: "Canonical case", output: "Routing disposition and findings", guardrail: "Recommendation-blocking defects stop routing.", aiContribution: "AI is permitted to reason only after deterministic data-quality conditions are satisfied." },
  { id: "missing", label: "Missing Information Agent", kind: "control", role: "Classifies absent or unresolved information by clinical importance and action needed.", input: "Quality-checked case", output: "Blocking and non-blocking missing-information plan", guardrail: "Low information produces abstention or a request for information.", aiContribution: "AI turns uncertainty into an actionable worklist rather than quietly filling gaps." },
  { id: "context", label: "Per-request WorkflowContext", kind: "control", role: "Creates an immutable registry of agents and governed evidence dependencies for one case request.", input: "Deployment configuration and approved evidence stores", output: "Isolated runtime dependencies", guardrail: "Concurrent users cannot overwrite one another's evidence configuration.", aiContribution: "The architecture supports safe multi-user agent orchestration without shared mutable clinical state." },
  { id: "router", label: "Deterministic clinical router", kind: "control", role: "Maps the represented clinical question to required and conditional specialist domains.", input: "Gate-cleared canonical case", output: "Explicit RoutingDecision", guardrail: "Routing is rule-based, inspectable, and does not generate a recommendation.", aiContribution: "The right experts are invoked for the question while unrelated agents remain out of the workflow." },
  { id: "guideline", label: "Guideline Agent", kind: "agent", role: "Evaluates formal or consensus guidance matched to represented disease context.", input: "Case plus governed guideline records", output: "Bounded guideline report", guardrail: "No verified source means no guideline claim.", aiContribution: "AI maps complex case features to the relevant portion of governed guidance." },
  { id: "molecular", label: "Molecular Agent", kind: "agent", role: "Interprets represented variants against governed molecular evidence.", input: "Verified molecular findings and evidence records", output: "Clinical actionability report", guardrail: "Biological plausibility is not clinical actionability.", aiContribution: "AI connects genomic findings to disease context while preserving evidence level and limitations." },
  { id: "translational", label: "Translational Agent", kind: "agent", role: "Explains mechanisms and resistance biology without converting preclinical signals into treatment claims.", input: "Case, molecular findings, translational evidence", output: "Mechanistic report", guardrail: "Preclinical evidence cannot independently support clinical action.", aiContribution: "AI makes complex biology understandable for multidisciplinary discussion." },
  { id: "literature", label: "Literature Agent", kind: "agent", role: "Retrieves and filters current literature for the represented population and question.", input: "Bounded PubMed query concepts", output: "Literature discovery report", guardrail: "Discovery is not verification and population mismatch is explicit.", aiContribution: "AI reduces search burden and organizes publications around the clinical question." },
  { id: "trials", label: "Clinical Trials Agent", kind: "agent", role: "Identifies conservative possible matches from official registry data.", input: "Diagnosis, molecular concepts, age, and registry records", output: "Possible trial-match report", guardrail: "Trial matching is never presented as eligibility.", aiContribution: "AI can rapidly narrow a large registry while leaving eligibility determination to the trial team." },
  { id: "safety", label: "Safety Agent", kind: "agent", role: "Reviews official safety evidence for represented and governed candidate therapies.", input: "Patient context, candidate therapies, safety records", output: "Contraindication and monitoring report", guardrail: "A non-match is not evidence that risk is absent.", aiContribution: "AI brings patient factors and therapy-specific safety information into the same review." },
  { id: "gateway", label: "Evidence Gateway", kind: "evidence", role: "Controls which retrieved evidence may enter governed specialist reasoning.", input: "Official-source discovery records", output: "Admitted, limited, or rejected evidence", guardrail: "Licensing, source identity, verification, and attestation remain explicit.", aiContribution: "AI retrieval remains separated from the governance decision to admit evidence." },
  { id: "verifier", label: "Evidence Verifier", kind: "evidence", role: "Checks source spans, identifiers, dates, and claim alignment before propagation.", input: "Candidate evidence and proposed claims", output: "Verification status with source trace", guardrail: "Failed verification does not propagate.", aiContribution: "AI-assisted review is constrained by a separate verification contract." },
  { id: "redteam", label: "Clinical Red Team", kind: "control", role: "Challenges the combined specialist package for unsupported claims, conflicts, and unsafe assumptions.", input: "Case, routing decision, specialist reports", output: "Blocking and non-blocking challenge findings", guardrail: "Unsafe synthesis is stopped before consensus.", aiContribution: "A dedicated challenge layer tests the system's own conclusions instead of rewarding agreement." },
  { id: "consensus", label: "Evidence-weighted consensus", kind: "control", role: "Integrates management candidates using explicit evidence and safety rules.", input: "Specialist outputs and Red Team report", output: "Decision state, options, conditions, uncertainty", guardrail: "Agent agreement is not truth; consensus is not voting.", aiContribution: "AI synthesizes multiple bounded perspectives without hiding disagreement or uncertainty." },
  { id: "brief", label: "Brief renderer", kind: "output", role: "Transforms governed outputs into a structured tumor-board discussion package.", input: "Consensus, evidence, uncertainty, and source traces", output: "Decision-ready Tumor Board Intelligence Brief", guardrail: "The renderer cannot create new clinical claims.", aiContribution: "AI compresses a complex review into a usable multidisciplinary briefing." },
  { id: "decision", label: "Clinician judgment & board decision", kind: "human", role: "Records human interpretation, discussion, and the eventual multidisciplinary decision separately from system synthesis.", input: "Governed brief plus real-world clinical judgment", output: "Human-authored board decision", guardrail: "The system remains decision support, not autonomous care.", aiContribution: "AI improves preparation and visibility while clinical accountability remains human." },
  { id: "versionstore", label: "Immutable case version store", kind: "control", role: "Persists the complete governed case, evidence review, workflow output, and human decision as an append-only snapshot.", input: "Completed governed decision package", output: "Content-hashed version with parent lineage", guardrail: "A saved decision is never overwritten; later information creates a child version.", aiContribution: "Structured version history lets AI-assisted reviews be compared over time without erasing the evidence and judgment that supported an earlier decision." },
  { id: "impact", label: "New-information impact planner", kind: "control", role: "Compares a proposed source-linked update with its selected base version and maps changed fields to downstream dependencies.", input: "Base version plus attested canonical case update", output: "Changed paths, affected specialists, and mandatory controls", guardrail: "The prior human decision becomes historical only and cannot be silently carried forward.", aiContribution: "AI workflow effort can be focused where information changed while a deterministic dependency map controls reuse permission." },
  { id: "targeted", label: "Targeted rerun orchestrator", kind: "control", role: "Runs affected specialists, reuses only schema-valid unaffected reports, and repeats every safety and synthesis control.", input: "Impact plan, updated case, re-commissioned evidence, prior specialist reports", output: "New governed workflow with execution and reuse receipt", guardrail: "Integrity gates, routing, Clinical Red Team, consensus, and brief rendering always run again.", aiContribution: "The system reduces avoidable repeated work without treating an old specialist answer as valid for changed clinical inputs." },
  { id: "evaluation", label: "Deterministic evaluation harness", kind: "control", role: "Replays explicit governance invariants across workflow packages and saved case versions.", input: "Workflow result, evidence attestation, human decision, and reuse audit events", output: "Per-gate results, primary measures, and zero-tolerance guardrail counts", guardrail: "It measures software governance behavior, not clinical correctness or patient benefit.", aiContribution: "AI-assisted workflows become testable systems because their safety boundaries, provenance, and human handoffs are evaluated independently of generated prose." },
  { id: "security", label: "API security boundary", kind: "control", role: "Restricts hosts and origins, bounds request size, disables unsafe caching, and adds browser-facing response protections.", input: "Deployment configuration and every HTTP request", output: "Accepted bounded request or explicit rejection with protected response headers", guardrail: "Production identity, shared rate limiting, monitoring, and secure transport must be supplied by the deployment environment.", aiContribution: "Secure delivery limits how a useful AI service can be reached and abused without pretending application code replaces institutional security operations." },
  { id: "release", label: "Release readiness gate", kind: "output", role: "Separates local software readiness, production research controls, and institutional clinical authorization.", input: "Evaluation results plus live deployment configuration", output: "Inspectable ready or blocked checks with remediation", guardrail: "Clinical release remains blocked in research code even when every software test passes.", aiContribution: "The system makes AI maturity visible while preventing technical success from being misrepresented as clinical validation." },
];

const byId = Object.fromEntries(nodes.map((node) => [node.id, node])) as Record<string, ArchitectureNode>;

const layers = [
  { label: "01 · Intake and representation", nodes: ["sources", "extraction", "canonical", "confirmation"] },
  { label: "02 · Deterministic safety gates", nodes: ["semantic", "integrity", "missing"] },
  { label: "03 · Request-isolated orchestration", nodes: ["context", "router"] },
  { label: "04 · Parallel specialist intelligence", nodes: ["guideline", "molecular", "translational", "literature", "trials", "safety"] },
  { label: "05 · Governed evidence services", nodes: ["gateway", "verifier"] },
  { label: "06 · Challenge, synthesis, and decision", nodes: ["redteam", "consensus", "brief", "decision"] },
  { label: "07 · Version lineage and governed updates", nodes: ["versionstore", "impact", "targeted"] },
  { label: "08 · Evaluation, security, and release controls", nodes: ["evaluation", "security", "release"] },
];

export function ArchitectureView() {
  const [selectedId, setSelectedId] = useState("context");
  const selected = byId[selectedId];

  return (
    <section className="architecture-experience" aria-labelledby="architecture-title">
      <header className="architecture-header">
        <div>
          <p className="micro-label">Detailed agentic system architecture</p>
          <h1 id="architecture-title">AI accelerates the work. Governance controls what can influence a decision.</h1>
          <p>Select any component to inspect its role, input, output, AI contribution, and governing safety rule.</p>
        </div>
        <div className="architecture-legend" aria-label="Architecture node legend">
          <span><i className="legend-human" />Human authority</span>
          <span><i className="legend-control" />Control layer</span>
          <span><i className="legend-agent" />AI agent</span>
          <span><i className="legend-evidence" />Evidence service</span>
        </div>
      </header>

      <div className="architecture-body">
        <div className="architecture-map" role="group" aria-label="Tumor Board Intelligence system flow">
          {layers.map((layer, layerIndex) => (
            <div className="architecture-layer-wrap" key={layer.label}>
              <section className="architecture-layer">
                <p>{layer.label}</p>
                <div className={`architecture-node-grid nodes-${layer.nodes.length}`}>
                  {layer.nodes.map((nodeId) => {
                    const node = byId[nodeId];
                    return (
                      <button
                        type="button"
                        key={node.id}
                        className={`architecture-node ${node.kind} ${selectedId === node.id ? "selected" : ""}`}
                        aria-pressed={selectedId === node.id}
                        onClick={() => setSelectedId(node.id)}
                      >
                        <small>{node.kind}</small>
                        <strong>{node.label}</strong>
                      </button>
                    );
                  })}
                </div>
              </section>
              {layerIndex < layers.length - 1 && <div className="architecture-connector" aria-hidden="true"><span>↓</span></div>}
            </div>
          ))}
          <div className="cross-cutting-row">
            <span>Provenance ledger</span>
            <span>Structured audit events</span>
            <span>Fail-closed source configuration</span>
            <span>Research-use boundary</span>
          </div>
        </div>

        <aside className="architecture-detail" aria-live="polite">
          <p className="micro-label">Selected component</p>
          <h2>{selected.label}</h2>
          <dl>
            <div><dt>Role</dt><dd>{selected.role}</dd></div>
            <div><dt>Input</dt><dd>{selected.input}</dd></div>
            <div><dt>Output</dt><dd>{selected.output}</dd></div>
            <div className="ai-detail"><dt>How AI helps</dt><dd>{selected.aiContribution}</dd></div>
            <div className="guardrail-detail"><dt>Governing rule</dt><dd>{selected.guardrail}</dd></div>
          </dl>
        </aside>
      </div>
    </section>
  );
}
