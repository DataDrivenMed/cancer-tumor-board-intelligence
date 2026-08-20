"use client";

import { useEffect, useState } from "react";

import { ArchitectureView } from "./components/architecture-view";
import { AuthenticatedProduct } from "./components/authenticated-product";
import {
  BoardDecisionWorkspace,
  type BoardDecisionRecord,
} from "./components/board-decision-workspace";
import {
  CaseIntakeReview,
  type ConfirmedIntake,
  type IntakeAuditEvent,
} from "./components/case-intake-review";
import {
  EvidenceCommissioningReview,
  type CommissionedEvidenceReview,
  type EvidenceReviewEvent,
} from "./components/evidence-commissioning-review";
import { GovernedAnalysisReview } from "./components/governed-analysis-review";
import { ProductHome } from "./components/product-home";
import { EvaluationReleaseConsole } from "./components/evaluation-release-console";
import {
  CaseVersionWorkspace,
  type PendingCaseUpdate,
} from "./components/case-version-workspace";
import { syntheticCase } from "./data/synthetic-case";
import type { ReviewFact } from "./data/synthetic-intake";
import {
  type ApiConnectionState,
  type CaseVersionDetail,
  type CaseVersionSummary,
  type RuntimeStatus,
  type WorkflowRunResponse,
  getCaseVersion,
  getRuntimeStatus,
  runCommissionedWorkflow,
  runTargetedWorkflow,
} from "./lib/tumor-board-api";

type Stage = "intake" | "verify" | "evidence" | "analyze" | "brief";
type InspectorTab = "evidence" | "activity" | "audit";
type Workspace = "home" | "clinical" | "research";
type ResearchView = "architecture" | "qualification" | "evaluation";

const stages: { id: Stage; label: string; note: string }[] = [
  { id: "intake", label: "Intake", note: "Sources & question" },
  { id: "verify", label: "Verify", note: "Facts & gaps" },
  { id: "evidence", label: "Evidence", note: "Governed sources" },
  { id: "analyze", label: "Analyze", note: "Challenge & synthesis" },
  { id: "brief", label: "Brief", note: "Board-ready output" },
];

const stageContent: Record<
  Stage,
  { kicker: string; title: string; description: string }
> = {
  intake: {
    kicker: "Case intake",
    title: "Build the clinical question from the record",
    description:
      "Review the represented source material, confirm the patient snapshot, and frame the exact question the board needs to answer.",
  },
  verify: {
    kicker: "Representation review",
    title: "Confirm what is known before reasoning begins",
    description:
      "Decision-critical facts, conflicts, and missing information stay visible. Corrections are appended to the audit history rather than erasing the record.",
  },
  evidence: {
    kicker: "Evidence review",
    title: "Inspect evidence by clinical question",
    description:
      "Guidelines, literature, molecular evidence, safety sources, and possible trials remain separated by evidence type and verification status.",
  },
  analyze: {
    kicker: "Governed analysis",
    title: "Challenge the package before synthesis",
    description:
      "The Clinical Red Team checks unsupported claims and unsafe assumptions before the consensus engine can prepare management options.",
  },
  brief: {
    kicker: "Tumor-board brief",
    title: "Prepare a decision-ready discussion package",
    description:
      "System synthesis, clinician judgment, and the board's eventual decision remain separate so the final record shows who decided what.",
  },
};

function StatusPill({ tone, children }: { tone: string; children: React.ReactNode }) {
  return <span className={`status-pill ${tone}`}>{children}</span>;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function asRecords(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value) ? value.map(asRecord) : [];
}

function readable(value: unknown, fallback = "Not represented"): string {
  if (typeof value === "string" && value.trim()) return value.replaceAll("_", " ");
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return fallback;
}

function StagePanel({
  stage,
  workflow,
  intakeConfirmed,
  onIntakeDirty,
  onIntakeConfirmed,
  confirmedFacts,
  intakeSnapshot,
  casePayload,
  connection,
  evidenceReview,
  onEvidenceDirty,
  onEvidenceCommissioned,
  onOpenEvidence,
  running,
  onRunAnalysis,
  boardDecisionRecord,
  onBoardDecisionDirty,
  onBoardDecisionRecorded,
  intakeMode,
  intakeKey,
  syntheticOnly,
}: {
  stage: Stage;
  workflow: WorkflowRunResponse | null;
  intakeConfirmed: boolean;
  onIntakeDirty: () => void;
  onIntakeConfirmed: (result: ConfirmedIntake) => void;
  confirmedFacts: ReviewFact[];
  intakeSnapshot: ConfirmedIntake | null;
  casePayload: Record<string, unknown>;
  connection: ApiConnectionState;
  evidenceReview: CommissionedEvidenceReview | null;
  onEvidenceDirty: () => void;
  onEvidenceCommissioned: (result: CommissionedEvidenceReview) => void;
  onOpenEvidence: () => void;
  running: boolean;
  onRunAnalysis: () => void;
  boardDecisionRecord: BoardDecisionRecord | null;
  onBoardDecisionDirty: () => void;
  onBoardDecisionRecorded: (record: BoardDecisionRecord) => void;
  intakeMode: "guided" | "upload";
  intakeKey: number;
  syntheticOnly: boolean;
}) {
  if (stage === "intake") {
    return <CaseIntakeReview key={intakeKey} confirmed={intakeConfirmed} initialIntake={intakeSnapshot} initialMode={intakeMode} syntheticOnly={syntheticOnly} onDirty={onIntakeDirty} onConfirmed={onIntakeConfirmed} />;
  }

  if (stage === "verify") {
    const missingReport = asRecord(workflow?.result.missing_information_report);
    const missingItems = asRecords(missingReport.items);
    const integrityReport = asRecord(workflow?.result.case_integrity_report);
    return (
      <div className="panel-stack">
        <section className="editorial-card">
          <div className="card-heading-row">
            <div><p className="micro-label">Decision-critical facts</p><h3>Representation checklist</h3></div>
            <span className="quiet-count">5 source-linked domains</span>
          </div>
          <div className="fact-grid">
            {(confirmedFacts.length ? confirmedFacts : [
              { id: "pending", label: "Clinician-confirmed representation", value: "Not yet confirmed", reviewState: "pending" },
            ]).map((item) => (
              <div className={`fact-item ${item.reviewState === "corrected" ? "corrected-item" : ""}`} key={item.id}><span className="check-mark">{item.reviewState === "corrected" ? "↺" : "✓"}</span><div><strong>{item.label}</strong><small>{item.value} · {item.reviewState === "corrected" ? "clinician corrected" : "source accepted"}</small></div></div>
            ))}
            {missingItems.slice(0, 3).map((item, index) => (
              <div className="fact-item attention-item" key={`${readable(item.field)}-${index}`}><span className="attention-mark">!</span><div><strong>{readable(item.field)}</strong><small>{readable(item.reason, "Backend identified missing information")}</small></div></div>
            ))}
          </div>
        </section>
        <section className={`editorial-card ${workflow ? "verification-result-card" : "conflict-card"}`}>
          <p className="micro-label">Deterministic verification</p>
          <h3>{workflow ? `Case integrity: ${readable(integrityReport.disposition, "completed")}` : "Awaiting governed workflow run"}</h3>
          <p className="supporting-copy">{workflow ? `${missingItems.length} missing-information items were returned by the backend and remain explicit.` : "The API will run semantic integrity, case integrity, and missing-information gates before specialist routing."}</p>
          {!workflow && <button className="primary-button full-button" type="button" onClick={onOpenEvidence}>Continue to evidence commissioning</button>}
        </section>
      </div>
    );
  }

  if (stage === "evidence") {
    return (
      <EvidenceCommissioningReview
        casePayload={casePayload}
        connection={connection}
        initialCommission={evidenceReview}
        onDirty={onEvidenceDirty}
        onCommissioned={onEvidenceCommissioned}
      />
    );
  }

  if (stage === "analyze") {
    return <GovernedAnalysisReview workflow={workflow} evidenceReady={evidenceReview?.validatedByApi === true} running={running} onRun={onRunAnalysis} />;
  }

  if (!workflow) {
    return (
      <section className="editorial-card connected-empty-state">
        <p className="micro-label">Tumor-board brief</p>
        <h3>The brief will appear after a governed workflow run</h3>
        <p>No synthetic recommendation text is substituted for a backend result.</p>
      </section>
    );
  }

  return (
    <BoardDecisionWorkspace
      workflow={workflow}
      connection={connection}
      initialRecord={boardDecisionRecord}
      onDirty={onBoardDecisionDirty}
      onRecorded={onBoardDecisionRecorded}
    />
  );
}

function Inspector({
  active,
  onChange,
  connection,
  runtime,
  workflow,
  intakeEvents,
  evidenceEvents,
  evidenceReview,
  extractionVersion,
  boardDecisionRecord,
  pendingUpdate,
  lastSavedVersion,
  caseType,
}: {
  active: InspectorTab;
  onChange: (tab: InspectorTab) => void;
  connection: ApiConnectionState;
  runtime: RuntimeStatus | null;
  workflow: WorkflowRunResponse | null;
  intakeEvents: IntakeAuditEvent[];
  evidenceEvents: EvidenceReviewEvent[];
  evidenceReview: CommissionedEvidenceReview | null;
  extractionVersion: string;
  boardDecisionRecord: BoardDecisionRecord | null;
  pendingUpdate: PendingCaseUpdate | null;
  lastSavedVersion: CaseVersionDetail | null;
  caseType: string;
}) {
  const channels = [
    ["guideline", "Formal guidance"],
    ["molecular", "Molecular evidence"],
    ["pubmed", "Literature discovery"],
    ["clinical_trials", "Trial registry"],
    ["safety", "Safety evidence"],
  ] as const;
  const channelRows = channels.map(([id, label]) => {
    const status = runtime?.[id] || {};
    const ready = status.ready === true || status.loaded === true;
    const reason = readable(status.reason, ready ? "Configured and ready" : readable(status.configuration_origin, "Fail-closed or not configured"));
    return { id, label, ready, reason };
  });
  const readyCount = channelRows.filter((row) => row.ready).length;
  const events = workflow?.events || [];
  const approvedEvidence = evidenceReview?.decisions.filter((item) => item.decision === "approved").length || 0;
  const rejectedEvidence = evidenceReview?.decisions.filter((item) => item.decision === "rejected").length || 0;

  return (
    <aside className="inspector" aria-label="Case inspector">
      <div className="inspector-tabs" role="tablist" aria-label="Inspector views">
        {(["evidence", "activity", "audit"] as InspectorTab[]).map((tab) => (
          <button key={tab} className={active === tab ? "active" : ""} onClick={() => onChange(tab)} role="tab" aria-selected={active === tab}>{tab}</button>
        ))}
      </div>

      {active === "evidence" && (
        <div className="inspector-content">
          <div className="inspector-intro"><p className="micro-label">Backend evidence status</p><h2>Source readiness</h2><p>Readiness comes from the Phase 1 API and describes system capability, not patient-specific treatment appropriateness.</p></div>
          {evidenceReview && <div className="commission-score"><div><span>{approvedEvidence}</span><small>approved</small></div><div><span>{rejectedEvidence}</span><small>rejected</small></div><p>{evidenceReview.validatedByApi ? "Candidate set validated by FastAPI" : "Local review preview only"}</p></div>}
          {runtime ? (
            <>
              <div className="readiness-score"><div><span>{readyCount}</span><small>ready streams</small></div><div><span>{channelRows.length - readyCount}</span><small>limited streams</small></div></div>
              {channelRows.map((row) => (
                <div className="source-item" key={row.id}><span className={`source-dot ${row.ready ? "ready" : "limited"}`} /><div><strong>{row.label}</strong><small>{row.reason}</small></div></div>
              ))}
            </>
          ) : (
            <div className="inspector-empty"><strong>{connection === "checking" ? "Checking the API" : "API status unavailable"}</strong><p>Start or reconnect the FastAPI service to load governed source readiness.</p></div>
          )}
        </div>
      )}

      {active === "activity" && (
        <div className="inspector-content">
          <div className="inspector-intro"><p className="micro-label">Backend workflow activity</p><h2>What the system did</h2><p>Every item below is derived from a real structured audit event returned by FastAPI.</p></div>
          {events.length ? (
            <div className="activity-list">
              {events.map((event) => (
                <div className="activity-item" key={event.event_id}>
                  <div className="activity-rail"><span>{event.sequence}</span></div>
                  <div><strong>{event.title}</strong><p>{event.clinical_consequence}</p><small>{event.source_event}</small></div>
                </div>
              ))}
            </div>
          ) : (
            <div className="inspector-empty"><strong>No workflow events yet</strong><p>Run the governed synthetic case to populate this activity record.</p></div>
          )}
          <p className="inspector-footnote">Hidden reasoning is not requested, stored, or displayed.</p>
        </div>
      )}

      {active === "audit" && (
        <div className="inspector-content">
          <div className="inspector-intro"><p className="micro-label">Technical audit</p><h2>Structured trace</h2><p>Technical detail is available when needed without crowding the clinical workspace.</p></div>
          <dl className="audit-list">
            <div><dt>Case type</dt><dd>{caseType.replaceAll("_", " ")}</dd></div>
            <div><dt>Schema</dt><dd>0.3.0</dd></div>
            <div><dt>API contract</dt><dd>{workflow?.api_version || "0.6.0"}</dd></div>
            <div><dt>Extraction</dt><dd>{extractionVersion}</dd></div>
            <div><dt>Intake review events</dt><dd>{intakeEvents.length}</dd></div>
            <div><dt>Context</dt><dd>Per request</dd></div>
            <div><dt>Evidence mode</dt><dd>{evidenceReview?.mode.replaceAll("_", " ") || "Fail closed"}</dd></div>
            <div><dt>Candidate set</dt><dd>{evidenceReview?.validatedByApi ? "API validated" : evidenceReview ? "Local preview" : "Not reviewed"}</dd></div>
            <div><dt>Evidence decisions</dt><dd>{evidenceReview?.decisions.length || 0}</dd></div>
            <div><dt>Reasoning trace</dt><dd>Not stored</dd></div>
            <div><dt>Request ID</dt><dd>{workflow?.request_id || "Not run"}</dd></div>
            <div><dt>Human decision</dt><dd>{boardDecisionRecord ? "API validated" : "Not recorded"}</dd></div>
            <div><dt>Case version</dt><dd>{lastSavedVersion ? `Saved v${lastSavedVersion.version_number}` : "Not saved"}</dd></div>
            <div><dt>Update lineage</dt><dd>{pendingUpdate ? "Child version pending" : workflow?.rerun ? "Targeted rerun complete" : "No active update"}</dd></div>
            <div><dt>Specialist reuse</dt><dd>{workflow?.rerun ? workflow.rerun.specialist_agents_reused.length : 0}</dd></div>
          </dl>
          {intakeEvents.length > 0 && <div className="intake-audit-list">{intakeEvents.slice(-5).map((item) => <div key={item.id}><strong>{item.action.replaceAll("_", " ")}</strong><span>{item.detail}</span></div>)}</div>}
          {evidenceEvents.length > 0 && <div className="evidence-audit-list">{evidenceEvents.slice(-6).map((item) => <div key={item.id}><strong>{item.action.replaceAll("_", " ")}</strong><span>{item.detail}</span></div>)}</div>}
          {boardDecisionRecord && <div className="evidence-audit-list">{boardDecisionRecord.decision_events.map((item) => <div key={`${item.event}-${item.timestamp}`}><strong>{item.event.replaceAll("_", " ")}</strong><span>{item.detail}</span></div>)}</div>}
          <p className="inspector-footnote">The request identifier links the interface result to the backend activity and audit package.</p>
        </div>
      )}
    </aside>
  );
}

function ResearchConsole({ connection }: { connection: ApiConnectionState }) {
  const [view, setView] = useState<ResearchView>("architecture");
  const title = view === "architecture"
    ? "See how the governed AI system works"
    : view === "qualification"
      ? "System evidence, kept separate from patient review"
      : "Measure software governance before release";
  const description = view === "architecture"
    ? "A detailed, inspectable map connects every AI contribution to its evidence boundary, safety gate, and human decision point."
    : view === "qualification"
      ? "Qualification history, pathway readiness, and source governance are assessed here without entering the clinician workspace."
      : "Deterministic metrics, security configuration, accessibility controls, and release blockers remain visible and testable.";
  return (
    <main className="research-main" id="main-content" tabIndex={-1}>
      <header className="research-header">
        <div><p className="micro-label">Research & qualification console</p><h1>{title}</h1><p>{description}</p></div>
        <StatusPill tone="neutral">Research preview</StatusPill>
      </header>
      <nav className="research-view-tabs" aria-label="Research console views" role="tablist">
        <button type="button" role="tab" className={view === "architecture" ? "active" : ""} aria-selected={view === "architecture"} onClick={() => setView("architecture")}>Architecture</button>
        <button type="button" role="tab" className={view === "qualification" ? "active" : ""} aria-selected={view === "qualification"} onClick={() => setView("qualification")}>Qualification evidence</button>
        <button type="button" role="tab" className={view === "evaluation" ? "active" : ""} aria-selected={view === "evaluation"} onClick={() => setView("evaluation")}>Evaluation & release</button>
      </nav>
      {view === "architecture" ? <ArchitectureView /> : view === "evaluation" ? <EvaluationReleaseConsole connection={connection} /> : (
        <>
          <section className="qualification-grid">
            <article className="qualification-card featured"><p className="micro-label">Whole-system qualification</p><strong className="large-number">36/36</strong><h2>Controlled cases passed</h2><p>Frozen post-extraction integration protocol with zero observed safety-stop violations.</p><small>Historical qualification · v1.0.0</small></article>
            <article className="qualification-card"><p className="micro-label">Extraction remediation</p><strong className="large-number">30/30</strong><h2>Strict executions passed</h2><p>Exact provenance anchors remained intact across the controlled benchmark.</p><small>Frozen benchmark · v2.5</small></article>
            <article className="qualification-card"><p className="micro-label">Pathway registry</p><strong className="large-number">14</strong><h2>Oncology programs registered</h2><p>Architecture support does not automatically establish disease-specific clinical validation.</p><small>Pan-oncology common core</small></article>
          </section>
          <section className="editorial-card qualification-table-card">
            <div className="card-heading-row"><div><p className="micro-label">Pathway readiness</p><h3>Qualification state by program</h3></div><StatusPill tone="neutral">Governed protocol</StatusPill></div>
            <div className="program-row program-head"><span>Program</span><span>Architecture</span><span>Qualification</span><span>Clinical release</span></div>
            <div className="program-row"><strong>Hematologic malignancies</strong><StatusPill tone="verified">Ready</StatusPill><StatusPill tone="verified">Software qualified</StatusPill><StatusPill tone="limited">Not established</StatusPill></div>
            <div className="program-row"><strong>Breast oncology</strong><StatusPill tone="verified">Ready</StatusPill><StatusPill tone="neutral">Protocol required</StatusPill><StatusPill tone="limited">Not established</StatusPill></div>
            <div className="program-row"><strong>Thoracic oncology</strong><StatusPill tone="verified">Ready</StatusPill><StatusPill tone="neutral">Protocol required</StatusPill><StatusPill tone="limited">Not established</StatusPill></div>
          </section>
        </>
      )}
    </main>
  );
}

function ProductWorkspace() {
  const syntheticOnly = process.env.NEXT_PUBLIC_DEPLOYMENT_PROFILE === "synthetic_evaluation";
  const [stage, setStage] = useState<Stage>("intake");
  const [inspectorTab, setInspectorTab] = useState<InspectorTab>("evidence");
  const [workspace, setWorkspace] = useState<Workspace>("home");
  const [intakeMode, setIntakeMode] = useState<"guided" | "upload">("guided");
  const [intakeKey, setIntakeKey] = useState(0);
  const [showVersions, setShowVersions] = useState(false);
  const [connection, setConnection] = useState<ApiConnectionState>("checking");
  const [runtime, setRuntime] = useState<RuntimeStatus | null>(null);
  const [workflow, setWorkflow] = useState<WorkflowRunResponse | null>(null);
  const [workflowError, setWorkflowError] = useState("");
  const [running, setRunning] = useState(false);
  const [casePayload, setCasePayload] = useState<Record<string, unknown>>(syntheticCase);
  const [rawExtraction, setRawExtraction] = useState<Record<string, unknown> | null>(null);
  const [intakeFacts, setIntakeFacts] = useState<ReviewFact[]>([]);
  const [intakeEvents, setIntakeEvents] = useState<IntakeAuditEvent[]>([]);
  const [extractionVersion, setExtractionVersion] = useState("Awaiting review");
  const [intakeConfirmed, setIntakeConfirmed] = useState(false);
  const [intakeSnapshot, setIntakeSnapshot] = useState<ConfirmedIntake | null>(null);
  const [evidenceReview, setEvidenceReview] = useState<CommissionedEvidenceReview | null>(null);
  const [evidenceEvents, setEvidenceEvents] = useState<EvidenceReviewEvent[]>([]);
  const [boardDecisionRecord, setBoardDecisionRecord] = useState<BoardDecisionRecord | null>(null);
  const [pendingUpdate, setPendingUpdate] = useState<PendingCaseUpdate | null>(null);
  const [lastSavedVersion, setLastSavedVersion] = useState<CaseVersionDetail | null>(null);
  const activeIndex = stages.findIndex((item) => item.id === stage);
  const content = stageContent[stage];
  const finalDecision = asRecord(workflow?.result.final_decision);
  const caseType = readable(casePayload.case_type, intakeMode === "upload" ? "deidentified_research" : "synthetic");

  const resetCaseSession = (mode: "guided" | "upload") => {
    if (syntheticOnly && mode === "upload") return;
    setIntakeMode(mode);
    setIntakeKey((current) => current + 1);
    setCasePayload(mode === "guided" ? structuredClone(syntheticCase) : {
      case_id: "Awaiting extraction",
      case_type: "deidentified_research",
    });
    setRawExtraction(null);
    setIntakeFacts([]);
    setIntakeEvents([]);
    setExtractionVersion("Awaiting review");
    setIntakeConfirmed(false);
    setIntakeSnapshot(null);
    setEvidenceReview(null);
    setEvidenceEvents([]);
    setWorkflow(null);
    setWorkflowError("");
    setBoardDecisionRecord(null);
    setPendingUpdate(null);
    setLastSavedVersion(null);
    setShowVersions(false);
    setStage("intake");
    setWorkspace("clinical");
  };

  const openSavedCase = async (item: CaseVersionSummary) => {
    setWorkflowError("");
    try {
      const response = await getCaseVersion(item.case_id, item.version_id);
      const version = response.version;
      setIntakeMode(version.case.case_type === "synthetic" ? "guided" : "upload");
      setIntakeKey((current) => current + 1);
      setCasePayload(version.case);
      setRawExtraction(version.raw_extraction);
      setWorkflow(version.workflow);
      setEvidenceReview(version.evidence_review as unknown as CommissionedEvidenceReview);
      setEvidenceEvents((version.evidence_review as unknown as CommissionedEvidenceReview).events || []);
      setBoardDecisionRecord(version.human_decision as BoardDecisionRecord);
      setLastSavedVersion(version);
      setIntakeConfirmed(true);
      setIntakeSnapshot(null);
      setPendingUpdate(null);
      setExtractionVersion("Restored from saved version");
      setShowVersions(false);
      setStage("brief");
      setWorkspace("clinical");
      setInspectorTab("audit");
    } catch (error) {
      setConnection("unavailable");
      setWorkflowError(error instanceof Error ? error.message : "The saved case could not be opened.");
      setWorkspace("clinical");
    }
  };

  useEffect(() => {
    let active = true;
    getRuntimeStatus()
      .then((response) => {
        if (!active) return;
        setRuntime(response.runtime_status);
        setConnection("ready");
      })
      .catch(() => {
        if (!active) return;
        setConnection("unavailable");
      });
    return () => { active = false; };
  }, []);

  const runWorkflow = async () => {
    setRunning(true);
    setWorkflowError("");
    try {
      if (!intakeConfirmed) {
        setStage("intake");
        return;
      }
      if (!evidenceReview?.validatedByApi) {
        setStage("evidence");
        return;
      }
      const evidenceCommission = {
        mode: evidenceReview.mode,
        candidate_set_id: evidenceReview.candidateSetId,
        decisions: evidenceReview.decisions,
        attested: evidenceReview.attested,
      };
      const response = pendingUpdate
        ? await runTargetedWorkflow({
            baseVersionId: pendingUpdate.baseVersionId,
            casePayload,
            rawExtraction,
            evidenceCommission,
            trigger: pendingUpdate.trigger,
            changeSummary: pendingUpdate.changeSummary,
          })
        : await runCommissionedWorkflow(casePayload, rawExtraction, evidenceCommission);
      setWorkflow(response);
      setBoardDecisionRecord(null);
      setRuntime(response.runtime_status);
      setConnection("ready");
      setInspectorTab("activity");
      setStage("analyze");
    } catch (error) {
      setConnection("unavailable");
      setWorkflowError(error instanceof Error ? error.message : "The governed workflow could not be reached.");
    } finally {
      setRunning(false);
    }
  };

  const markIntakeDirty = () => {
    setIntakeConfirmed(false);
    setWorkflow(null);
    setWorkflowError("");
    setEvidenceReview(null);
    setBoardDecisionRecord(null);
    setPendingUpdate(null);
    setLastSavedVersion(null);
  };

  const confirmIntake = (result: ConfirmedIntake) => {
    setCasePayload(result.casePayload);
    setRawExtraction(result.rawExtraction);
    setIntakeFacts(result.facts);
    setIntakeEvents(result.events);
    setExtractionVersion(result.extractionVersion);
    setIntakeSnapshot(result);
    setIntakeConfirmed(true);
    setWorkflow(null);
    setWorkflowError("");
    setEvidenceReview(null);
    setEvidenceEvents([]);
    setBoardDecisionRecord(null);
    setPendingUpdate(null);
    setLastSavedVersion(null);
    setInspectorTab("audit");
    setStage("verify");
  };

  const markEvidenceDirty = () => {
    setEvidenceReview(null);
    setWorkflow(null);
    setWorkflowError("");
    setBoardDecisionRecord(null);
  };

  const confirmEvidence = (result: CommissionedEvidenceReview) => {
    setEvidenceReview(result);
    setEvidenceEvents(result.events);
    setWorkflow(null);
    setWorkflowError("");
    setBoardDecisionRecord(null);
    setInspectorTab("audit");
  };

  const applyCaseUpdate = (update: PendingCaseUpdate) => {
    setPendingUpdate(update);
    setCasePayload(update.updatedCase);
    setRawExtraction(null);
    setIntakeConfirmed(true);
    setEvidenceReview(null);
    setEvidenceEvents([]);
    setWorkflow(null);
    setWorkflowError("");
    setBoardDecisionRecord(null);
    setLastSavedVersion(null);
    setInspectorTab("audit");
    setStage("evidence");
    setShowVersions(false);
  };

  const openStage = (nextStage: Stage) => {
    const nextIndex = stages.findIndex((item) => item.id === nextStage);
    if (nextIndex >= 2 && !intakeConfirmed) {
      setStage("intake");
      return;
    }
    if (nextIndex >= 3 && !evidenceReview?.validatedByApi) {
      setStage("evidence");
      return;
    }
    setStage(nextStage);
  };

  const diagnosis = asRecord(casePayload.diagnosis);
  const diseaseState = asRecord(casePayload.disease_state);
  const performance = asRecord(casePayload.performance_status);
  const molecular = asRecords(casePayload.molecular_findings)[0] || {};
  const evidenceValidated = evidenceReview?.validatedByApi === true;
  const primaryLabel = running
    ? pendingUpdate ? "Running targeted update…" : "Running commissioned workflow…"
    : workflow
      ? boardDecisionRecord ? "Decision package recorded" : "Review governed brief"
      : !intakeConfirmed
        ? "Confirm intake first"
        : !evidenceReview
          ? "Commission evidence next"
          : !evidenceValidated
            ? "Reconnect API to validate evidence"
            : pendingUpdate ? "Run targeted update workflow" : "Run commissioned workflow";

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Skip to primary content</a>
      <header className="topbar">
        <div className="brand-block"><div className="brand-mark" aria-hidden="true">TB</div><div><strong>Tumor Board Intelligence</strong><span>{syntheticOnly ? "Synthetic decision-support evaluation" : "Clinical decision-support workspace"}</span></div></div>
        <div className="topbar-actions"><span className="research-badge">{syntheticOnly ? "Synthetic evaluation" : "Research preview"}</span><span className={`connection-status ${connection}`} role="status" aria-live="polite"><i aria-hidden="true" /> {connection === "ready" ? "FastAPI connected" : connection === "checking" ? "Checking FastAPI" : "FastAPI unavailable"}</span>{!syntheticOnly && <a className="profile-button" href="/api/auth/logout" aria-label="Account and sign out">RP</a>}</div>
      </header>

      <div className="workspace-shell">
        <nav className="sidebar" aria-label="Product areas">
          <p className="nav-label">Workspaces</p>
          <button className={`workspace-button ${workspace === "home" ? "active" : ""}`} aria-pressed={workspace === "home"} onClick={() => setWorkspace("home")}><span>Home</span><small>Start or reopen a case</small></button>
          <button className={`workspace-button ${workspace === "clinical" ? "active" : ""}`} aria-pressed={workspace === "clinical"} onClick={() => setWorkspace("clinical")}><span>Clinical workspace</span><small>Case review and brief</small></button>
          <button className={`workspace-button ${workspace === "research" ? "active" : ""}`} aria-pressed={workspace === "research"} onClick={() => setWorkspace("research")}><span>Research console</span><small>Qualification and sources</small></button>
          <div className="nav-divider" />
          <p className="nav-label">Current case</p>
          <div className="case-nav-card"><span className="case-avatar">{readable(casePayload.case_id, "NEW").slice(0, 3)}</span><div><strong>{readable(casePayload.case_id, "New case")}</strong><small>{caseType === "synthetic" ? "Synthetic demonstration" : "De-identified clinical case"}</small></div></div>
          <div className="case-nav-meta"><div><span>Program</span><strong>Hematologic</strong></div><div><span>Priority</span><strong>Routine board</strong></div></div>
          <div className="sidebar-note"><span>Research boundary</span><p>{syntheticOnly ? "Synthetic teaching case only. Do not enter patient information." : "Use synthetic or fully de-identified cases only."}</p></div>
        </nav>

        {workspace === "home" ? (
          <ProductHome connection={connection} syntheticOnly={syntheticOnly} onStartSynthetic={() => resetCaseSession("guided")} onStartDeidentified={() => resetCaseSession("upload")} onOpenCase={(item) => void openSavedCase(item)} />
        ) : workspace === "research" ? (
          <ResearchConsole connection={connection} />
        ) : (
          <>
            <main className="clinical-main" id="main-content" tabIndex={-1}>
              <section className="case-header">
                <div><div className="case-title-row"><h1>{caseType === "synthetic" ? "Synthetic AML case review" : "De-identified case review"}</h1><StatusPill tone={workflow ? "verified" : intakeConfirmed ? "verified" : "attention"}>{lastSavedVersion ? `Saved version ${lastSavedVersion.version_number}` : boardDecisionRecord ? "Human decision recorded" : workflow ? readable(finalDecision.decision_state, "Workflow complete") : pendingUpdate ? "Update requires review" : intakeConfirmed ? "Intake confirmed" : "Review required"}</StatusPill></div><p>Case {readable(casePayload.case_id, "Awaiting extraction")} · {caseType === "synthetic" ? "Synthetic training use" : "De-identified research use"}</p></div>
                <div className="case-header-actions">
                  <button className="secondary-button" type="button" aria-pressed={showVersions} onClick={() => setShowVersions((current) => !current)}>{showVersions ? "Return to workflow" : "Versions & updates"}</button>
                  <button className="primary-button" type="button" disabled={running || !intakeConfirmed || Boolean(evidenceReview && !evidenceValidated)} onClick={() => workflow ? setStage("brief") : evidenceValidated ? void runWorkflow() : setStage("evidence")}>{primaryLabel}</button>
                </div>
              </section>

              {!showVersions && <nav className="stage-nav" aria-label="Clinical workflow stages">
                {stages.map((item, index) => (
                  <button key={item.id} aria-current={stage === item.id ? "step" : undefined} className={`${stage === item.id ? "active" : ""} ${index < activeIndex ? "complete" : ""}`} onClick={() => openStage(item.id)}><span className="stage-number">{index < activeIndex ? "✓" : index + 1}</span><span><strong>{item.label}</strong><small>{item.note}</small></span></button>
                ))}
              </nav>}

              <section className="content-area">
                {showVersions ? (
                  <CaseVersionWorkspace connection={connection} casePayload={casePayload} rawExtraction={rawExtraction} workflow={workflow} evidenceReview={evidenceReview} humanDecision={boardDecisionRecord} pendingUpdate={pendingUpdate} onApplyUpdate={applyCaseUpdate} onVersionSaved={(version) => { setLastSavedVersion(version); setPendingUpdate(null); setInspectorTab("audit"); }} onClose={() => setShowVersions(false)} />
                ) : (
                  <>
                    {workflowError && <div className="workflow-error" role="alert"><strong>FastAPI connection needed</strong><span>{workflowError} {syntheticOnly ? "The free evaluation service may be waking up. Wait about one minute, then retry." : "Start the local Python service and try again."}</span><button type="button" onClick={() => void runWorkflow()}>Retry</button></div>}
                    {pendingUpdate && <div className="workflow-update-notice" role="status"><strong>New information is active</strong><span>{pendingUpdate.changeSummary} Prior decisions remain historical and will not be carried forward.</span></div>}
                    <header className="section-heading"><p className="micro-label">{content.kicker}</p><h2>{content.title}</h2><p>{content.description}</p></header>
                    <div className="patient-strip" aria-label="Patient snapshot"><div><span>Age / sex</span><strong>{readable(casePayload.age)} · {readable(casePayload.sex)}</strong></div><div><span>Diagnosis</span><strong>{readable(diagnosis.value)}</strong></div><div><span>Disease state</span><strong>{readable(diseaseState.value)}</strong></div><div><span>Performance</span><strong>ECOG {readable(performance.value)}</strong></div><div><span>Molecular</span><strong>{molecular.gene ? `${readable(molecular.gene)}-${readable(molecular.alteration_type)}` : "Not represented"}</strong></div></div>
                    <StagePanel stage={stage} workflow={workflow} intakeConfirmed={intakeConfirmed} intakeSnapshot={intakeSnapshot} confirmedFacts={intakeFacts} onIntakeDirty={markIntakeDirty} onIntakeConfirmed={confirmIntake} casePayload={casePayload} connection={connection} evidenceReview={evidenceReview} onEvidenceDirty={markEvidenceDirty} onEvidenceCommissioned={confirmEvidence} onOpenEvidence={() => setStage("evidence")} running={running} onRunAnalysis={() => void runWorkflow()} boardDecisionRecord={boardDecisionRecord} onBoardDecisionDirty={() => setBoardDecisionRecord(null)} onBoardDecisionRecorded={(record) => { setBoardDecisionRecord(record); setInspectorTab("audit"); }} intakeMode={intakeMode} intakeKey={intakeKey} syntheticOnly={syntheticOnly} />
                  </>
                )}
              </section>
            </main>
            <Inspector active={inspectorTab} onChange={setInspectorTab} connection={connection} runtime={runtime} workflow={workflow} intakeEvents={intakeEvents} evidenceEvents={evidenceEvents} evidenceReview={evidenceReview} extractionVersion={extractionVersion} boardDecisionRecord={boardDecisionRecord} pendingUpdate={pendingUpdate} lastSavedVersion={lastSavedVersion} caseType={caseType} />
          </>
        )}
      </div>
    </div>
  );
}

export default function Home() {
  return <AuthenticatedProduct><ProductWorkspace /></AuthenticatedProduct>;
}
