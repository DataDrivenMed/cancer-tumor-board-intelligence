"use client";

import { useState } from "react";

import {
  type ApiConnectionState,
  type BoardDecisionOutcome,
  type ClinicianJudgmentPosition,
  type ClinicianJudgmentReason,
  type HumanDecisionRecordResponse,
  type WorkflowRunResponse,
  recordHumanDecision,
} from "../lib/tumor-board-api";

export type BoardDecisionRecord = HumanDecisionRecordResponse;

const judgmentOptions: { value: ClinicianJudgmentPosition; label: string; note: string }[] = [
  { value: "agree", label: "Agree", note: "The system-supported framing is suitable for board discussion." },
  { value: "partially_agree", label: "Partially agree", note: "Important qualifications or changes are needed." },
  { value: "disagree", label: "Disagree", note: "The clinician reaches a different interpretation." },
  { value: "insufficient_context", label: "Insufficient context", note: "The package is not ready for a judgment." },
];

const reasonOptions: { value: ClinicianJudgmentReason; label: string }[] = [
  { value: "clinical_context_not_represented", label: "Clinical context not represented" },
  { value: "evidence_interpretation_differs", label: "Evidence interpretation differs" },
  { value: "patient_preference", label: "Patient preference" },
  { value: "institutional_practice", label: "Institutional practice" },
  { value: "safety_concern", label: "Safety concern" },
  { value: "other", label: "Other" },
];

const outcomeOptions: { value: BoardDecisionOutcome; label: string }[] = [
  { value: "endorsed_system_supported_option", label: "Endorsed a system-supported option" },
  { value: "selected_alternative", label: "Selected an alternative" },
  { value: "deferred_pending_information", label: "Deferred pending information" },
  { value: "no_decision", label: "No decision reached" },
  { value: "other", label: "Other" },
];

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function asRecords(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value) ? value.map(asRecord) : [];
}

function asStrings(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function text(value: unknown, fallback = "Not represented"): string {
  if (typeof value === "string" && value.trim()) return value.replaceAll("_", " ");
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return fallback;
}

function shortId(value: string): string {
  return value.length > 18 ? `${value.slice(0, 10)}…${value.slice(-6)}` : value;
}

export function BoardDecisionWorkspace({
  workflow,
  connection,
  initialRecord,
  onDirty,
  onRecorded,
}: {
  workflow: WorkflowRunResponse;
  connection: ApiConnectionState;
  initialRecord: BoardDecisionRecord | null;
  onDirty: () => void;
  onRecorded: (record: BoardDecisionRecord) => void;
}) {
  const brief = asRecord(workflow.result.tumor_board_brief);
  const consensus = asRecord(workflow.result.consensus_report);
  const finalDecision = asRecord(workflow.result.final_decision);
  const caseRecord = asRecord(workflow.result.case);
  const briefSections = asRecords(brief.sections);
  const warnings = asStrings(brief.critical_warnings);
  const safeToRender = consensus.safe_to_render_decision_support === true;

  const [position, setPosition] = useState<ClinicianJudgmentPosition>(
    initialRecord?.clinician_judgment.position || "agree",
  );
  const [reasonCodes, setReasonCodes] = useState<ClinicianJudgmentReason[]>(
    initialRecord?.clinician_judgment.reason_codes || [],
  );
  const [clinicianRationale, setClinicianRationale] = useState(
    initialRecord?.clinician_judgment.rationale || "",
  );
  const [clinicianAttested, setClinicianAttested] = useState(
    initialRecord?.clinician_judgment.attested || false,
  );
  const [boardStatus, setBoardStatus] = useState<"pending" | "recorded">(
    initialRecord?.board_decision.status || "pending",
  );
  const [outcome, setOutcome] = useState<BoardDecisionOutcome | "">(
    initialRecord?.board_decision.outcome || "",
  );
  const [boardDecision, setBoardDecision] = useState(initialRecord?.board_decision.decision || "");
  const [boardRationale, setBoardRationale] = useState(initialRecord?.board_decision.rationale || "");
  const [boardDate, setBoardDate] = useState(initialRecord?.board_decision.board_date || "");
  const [boardAttested, setBoardAttested] = useState(initialRecord?.board_decision.attested || false);
  const [record, setRecord] = useState<BoardDecisionRecord | null>(initialRecord);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const clinicianReady = clinicianAttested
    && (position === "agree" || (reasonCodes.length > 0 && clinicianRationale.trim().length > 0));
  const boardReady = boardStatus === "pending"
    || Boolean(outcome && boardDecision.trim() && boardRationale.trim() && boardAttested);
  const canRecord = connection === "ready" && clinicianReady && boardReady && !saving;

  const systemSummary = {
    state: text(finalDecision.decision_state, text(brief.decision_state)),
    strength: text(finalDecision.decision_support_strength, text(brief.decision_support_strength)),
    primary: safeToRender
      ? text(finalDecision.primary_strategy, "No single primary strategy was selected")
      : text(finalDecision.abstention_reason, "Management synthesis was withheld by the governed workflow."),
  };

  const change = (action: () => void) => {
    action();
    setRecord(null);
    setError("");
    onDirty();
  };

  const toggleReason = (reason: ClinicianJudgmentReason) => {
    change(() => setReasonCodes((current) => (
      current.includes(reason) ? current.filter((item) => item !== reason) : [...current, reason]
    )));
  };

  const save = async () => {
    if (!canRecord) return;
    setSaving(true);
    setError("");
    try {
      const response = await recordHumanDecision({
        case_id: workflow.case_id,
        case_type: caseRecord.case_type === "deidentified_research" ? "deidentified_research" : "synthetic",
        workflow_request_id: workflow.request_id,
        system_decision: finalDecision,
        clinician_judgment: {
          position,
          reason_codes: reasonCodes,
          rationale: clinicianRationale.trim(),
          attested: clinicianAttested,
        },
        board_decision: {
          status: boardStatus,
          outcome: boardStatus === "recorded" && outcome ? outcome : null,
          decision: boardStatus === "recorded" ? boardDecision.trim() : "",
          rationale: boardStatus === "recorded" ? boardRationale.trim() : "",
          board_date: boardStatus === "recorded" && boardDate ? boardDate : null,
          attested: boardStatus === "recorded" && boardAttested,
        },
      });
      setRecord(response);
      onRecorded(response);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "The decision package could not be recorded.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="board-decision-workspace">
      <section className="board-summary-card print-board-section">
        <div className="board-summary-heading">
          <div>
            <p className="micro-label">Board-ready brief · governed system output</p>
            <h3>Decision package for {workflow.case_id}</h3>
            <p>{text(brief.summary, "The governed workflow returned a structured result for human review.")}</p>
          </div>
          <div className="board-summary-controls">
            <span className={`board-state-badge ${safeToRender ? "ready" : "withheld"}`}>
              {safeToRender ? "Decision support visible" : "Synthesis withheld safely"}
            </span>
            <button className="secondary-button print-control" type="button" onClick={() => window.print()}>
              Print / save as PDF
            </button>
          </div>
        </div>

        <div className="board-metrics">
          <div><span>Decision state</span><strong>{systemSummary.state}</strong></div>
          <div><span>Support strength</span><strong>{systemSummary.strength}</strong></div>
          <div><span>Source traces</span><strong>{text(brief.source_trace_count, "0")}</strong></div>
          <div><span>Workflow request</span><strong title={workflow.request_id}>{shortId(workflow.request_id)}</strong></div>
        </div>

        <div className={`system-strategy ${safeToRender ? "" : "withheld"}`}>
          <span>{safeToRender ? "System-supported strategy" : "Safe abstention"}</span>
          <p>{systemSummary.primary}</p>
        </div>

        {warnings.length > 0 && (
          <div className="board-warning-list">
            <strong>Critical warnings</strong>
            {warnings.map((warning) => <p key={warning}>{warning}</p>)}
          </div>
        )}

        <div className="brief-section-grid">
          {briefSections.map((section) => (
            <article key={text(section.section_id)}>
              <span>{text(section.title, "Brief section")}</span>
              {asRecords(section.items).slice(0, 3).map((item, index) => (
                <div key={`${text(item.label)}-${index}`}>
                  <strong>{text(item.label, "Finding")}</strong>
                  <p>{text(item.value)}</p>
                  <small>{text(item.epistemic_label, "Governed output")} · {asStrings(item.source_refs).length} source refs</small>
                </div>
              ))}
            </article>
          ))}
        </div>
      </section>

      <section className="decision-boundary-callout">
        <div><span>1</span><strong>System synthesis</strong><small>Produced by governed AI workflow</small></div>
        <i aria-hidden="true">→</i>
        <div><span>2</span><strong>Clinician judgment</strong><small>Attested human interpretation</small></div>
        <i aria-hidden="true">→</i>
        <div><span>3</span><strong>Board decision</strong><small>Collective clinical decision</small></div>
      </section>

      <section className="human-decision-card">
        <header>
          <div><p className="micro-label">Human layer 1</p><h3>Clinician judgment</h3></div>
          <p>Your judgment is appended to the record. It does not rewrite the system synthesis.</p>
        </header>
        <div className="judgment-options" role="radiogroup" aria-label="Clinician position">
          {judgmentOptions.map((option) => (
            <button
              key={option.value}
              type="button"
              role="radio"
              aria-checked={position === option.value}
              className={position === option.value ? "selected" : ""}
              onClick={() => change(() => setPosition(option.value))}
            >
              <strong>{option.label}</strong><small>{option.note}</small>
            </button>
          ))}
        </div>

        {position !== "agree" && (
          <div className="judgment-reasons">
            <label>Why does your judgment differ?</label>
            <div>
              {reasonOptions.map((reason) => (
                <button
                  key={reason.value}
                  type="button"
                  aria-pressed={reasonCodes.includes(reason.value)}
                  className={reasonCodes.includes(reason.value) ? "selected" : ""}
                  onClick={() => toggleReason(reason.value)}
                >
                  {reason.label}
                </button>
              ))}
            </div>
          </div>
        )}

        <label className="decision-field">
          <span>Clinician rationale {position === "agree" ? "(optional)" : "(required)"}</span>
          <textarea value={clinicianRationale} onChange={(event) => change(() => setClinicianRationale(event.target.value))} placeholder="Document the clinical interpretation, qualification, or missing context." />
        </label>
        <label className="attestation-row">
          <input type="checkbox" checked={clinicianAttested} onChange={(event) => change(() => setClinicianAttested(event.target.checked))} />
          <span>I attest that this clinician judgment reflects my review of the governed system package.</span>
        </label>
      </section>

      <section className="human-decision-card">
        <header>
          <div><p className="micro-label">Human layer 2</p><h3>Board decision</h3></div>
          <p>Record the collective decision now, or preserve an explicit pending state.</p>
        </header>
        <div className="board-status-switch" role="radiogroup" aria-label="Board decision status">
          <button type="button" role="radio" aria-checked={boardStatus === "pending"} className={boardStatus === "pending" ? "selected" : ""} onClick={() => change(() => setBoardStatus("pending"))}>Decision pending</button>
          <button type="button" role="radio" aria-checked={boardStatus === "recorded"} className={boardStatus === "recorded" ? "selected" : ""} onClick={() => change(() => setBoardStatus("recorded"))}>Record board decision</button>
        </div>

        {boardStatus === "recorded" && (
          <div className="board-decision-form">
            <label className="decision-field">
              <span>Outcome category</span>
              <select value={outcome} onChange={(event) => change(() => setOutcome(event.target.value as BoardDecisionOutcome))}>
                <option value="">Choose an outcome</option>
                {outcomeOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
            </label>
            <label className="decision-field">
              <span>Board date (optional)</span>
              <input type="date" value={boardDate} onChange={(event) => change(() => setBoardDate(event.target.value))} />
            </label>
            <label className="decision-field full-field">
              <span>Board decision</span>
              <textarea value={boardDecision} onChange={(event) => change(() => setBoardDecision(event.target.value))} placeholder="State what the board decided or will discuss with the patient." />
            </label>
            <label className="decision-field full-field">
              <span>Board rationale</span>
              <textarea value={boardRationale} onChange={(event) => change(() => setBoardRationale(event.target.value))} placeholder="Explain the clinical basis, including context outside the AI package." />
            </label>
            <label className="attestation-row full-field">
              <input type="checkbox" checked={boardAttested} onChange={(event) => change(() => setBoardAttested(event.target.checked))} />
              <span>I attest that this text accurately represents the tumor board&apos;s collective decision.</span>
            </label>
          </div>
        )}
      </section>

      <section className="decision-record-card print-board-section">
        <div className="decision-record-header">
          <div><p className="micro-label">Governed record</p><h3>Three-layer decision comparison</h3></div>
          <span>{record ? "API-validated receipt" : "Not yet recorded"}</span>
        </div>
        <div className="decision-comparison">
          <article><span>01 · System synthesis</span><strong>{systemSummary.state}</strong><p>{systemSummary.primary}</p><small>Immutable copy of workflow output</small></article>
          <article><span>02 · Clinician judgment</span><strong>{text(position)}</strong><p>{clinicianRationale || "No additional rationale entered."}</p><small>{clinicianAttested ? "Clinician attested" : "Attestation required"}</small></article>
          <article><span>03 · Board decision</span><strong>{boardStatus === "recorded" ? text(outcome) : "Pending"}</strong><p>{boardStatus === "recorded" ? boardDecision || "Decision text required." : "The collective board decision has not yet been recorded."}</p><small>{boardStatus === "recorded" && boardAttested ? "Board attested" : "Pending is explicitly preserved"}</small></article>
        </div>

        {error && <div className="decision-error" role="alert">{error}</div>}
        {record && (
          <div className="decision-receipt">
            <div><span>Decision record ID</span><strong title={record.decision_record_id}>{shortId(record.decision_record_id)}</strong></div>
            <div><span>Recorded at</span><strong>{new Date(record.recorded_at).toLocaleString()}</strong></div>
            <div><span>Storage state</span><strong>Validated receipt · not persisted</strong></div>
            <div><span>API contract</span><strong>{record.api_version}</strong></div>
          </div>
        )}

        <div className="decision-submit-row print-control">
          <p>{connection === "ready" ? "FastAPI will validate the attestations and return an audit receipt." : "Reconnect FastAPI before recording this package."}</p>
          <button className="primary-button" type="button" disabled={!canRecord} onClick={() => void save()}>
            {saving ? "Recording decision package…" : record ? "Record updated decision package" : "Record human decision package"}
          </button>
        </div>
      </section>
    </div>
  );
}
