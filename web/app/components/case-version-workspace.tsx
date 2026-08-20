"use client";

import { useEffect, useState } from "react";

import type { BoardDecisionRecord } from "./board-decision-workspace";
import type { CommissionedEvidenceReview } from "./evidence-commissioning-review";
import {
  type ApiConnectionState,
  type CaseUpdateAssessment,
  type CaseVersionDetail,
  type CaseVersionSummary,
  type CaseVersionTrigger,
  type WorkflowRunResponse,
  assessCaseUpdate,
  getCaseVersion,
  listCaseVersions,
  saveCaseVersion,
} from "../lib/tumor-board-api";

type UpdateField = "disease_state" | "performance_status" | "diagnosis" | "clinical_question" | "care_site";

export interface PendingCaseUpdate {
  baseVersionId: string;
  updatedCase: Record<string, unknown>;
  trigger: CaseVersionTrigger;
  changeSummary: string;
  assessment: CaseUpdateAssessment;
}

const fieldOptions: { value: UpdateField; label: string; hint: string }[] = [
  { value: "disease_state", label: "Disease state", hint: "For example: second relapse or refractory disease" },
  { value: "performance_status", label: "Performance status", hint: "Enter the new ECOG value from 0 to 5" },
  { value: "diagnosis", label: "Diagnosis", hint: "Use the exact represented diagnosis wording" },
  { value: "clinical_question", label: "Board question", hint: "State the revised question for the tumor board" },
  { value: "care_site", label: "Care site", hint: "Enter the represented care site" },
];

const triggerOptions: { value: CaseVersionTrigger; label: string }[] = [
  { value: "new_result", label: "New result" },
  { value: "new_document", label: "New document" },
  { value: "clinical_change", label: "Clinical change" },
  { value: "evidence_update", label: "Evidence update" },
  { value: "correction", label: "Correction" },
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

function readable(value: unknown, fallback = "Not represented"): string {
  if (typeof value === "string" && value.trim()) return value.replaceAll("_", " ");
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return fallback;
}

function clone(value: Record<string, unknown>): Record<string, unknown> {
  return JSON.parse(JSON.stringify(value)) as Record<string, unknown>;
}

function buildUpdatedCase(
  base: Record<string, unknown>,
  field: UpdateField,
  newValue: string,
  documentId: string,
  excerpt: string,
): Record<string, unknown> {
  const updated = clone(base);
  if (field === "clinical_question") {
    updated.clinical_question = { ...asRecord(updated.clinical_question), question: newValue.trim() };
  } else if (field === "care_site") {
    updated.care_site = newValue.trim();
  } else {
    const current = asRecord(updated[field]);
    const numericValue = field === "performance_status" ? Number(newValue) : newValue.trim();
    updated[field] = {
      ...current,
      field,
      value: numericValue,
      status: "confirmed",
      information_type: "observed",
      human_verified: true,
      provenance: [
        ...asRecords(current.provenance),
        {
          document_id: documentId.trim(),
          document_type: "new_information",
          source_excerpt: excerpt.trim(),
          source_segment_ids: [],
          source_verified: true,
        },
      ],
    };
  }
  const sources = Array.isArray(updated.source_documents)
    ? updated.source_documents.filter((item): item is string => typeof item === "string")
    : [];
  updated.source_documents = Array.from(new Set([...sources, documentId.trim()]));
  return updated;
}

function shortId(value: string): string {
  return value.length > 17 ? `${value.slice(0, 9)}…${value.slice(-5)}` : value;
}

export function CaseVersionWorkspace({
  connection,
  casePayload,
  rawExtraction,
  workflow,
  evidenceReview,
  humanDecision,
  pendingUpdate,
  onApplyUpdate,
  onVersionSaved,
  onClose,
}: {
  connection: ApiConnectionState;
  casePayload: Record<string, unknown>;
  rawExtraction: Record<string, unknown> | null;
  workflow: WorkflowRunResponse | null;
  evidenceReview: CommissionedEvidenceReview | null;
  humanDecision: BoardDecisionRecord | null;
  pendingUpdate: PendingCaseUpdate | null;
  onApplyUpdate: (update: PendingCaseUpdate) => void;
  onVersionSaved: (version: CaseVersionDetail) => void;
  onClose: () => void;
}) {
  const caseId = String(casePayload.case_id || "");
  const [versions, setVersions] = useState<CaseVersionSummary[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [selected, setSelected] = useState<CaseVersionDetail | null>(null);
  const [view, setView] = useState<"history" | "update">("history");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [assessing, setAssessing] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [field, setField] = useState<UpdateField>("disease_state");
  const [newValue, setNewValue] = useState("");
  const [trigger, setTrigger] = useState<CaseVersionTrigger>("new_result");
  const [documentId, setDocumentId] = useState("NEW-DOC-001");
  const [sourceExcerpt, setSourceExcerpt] = useState("");
  const [changeSummary, setChangeSummary] = useState("");
  const [attested, setAttested] = useState(false);
  const [assessment, setAssessment] = useState<CaseUpdateAssessment | null>(null);
  const [proposedCase, setProposedCase] = useState<Record<string, unknown> | null>(null);

  const loadVersions = async (preferredId?: string) => {
    if (!caseId || connection !== "ready") {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const response = await listCaseVersions(caseId);
      setVersions(response.versions);
      const nextId = preferredId || selectedId || response.versions[0]?.version_id || "";
      setSelectedId(nextId);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Case versions could not be loaded.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!caseId || connection !== "ready") return;
    let active = true;
    listCaseVersions(caseId)
      .then((response) => {
        if (!active) return;
        setVersions(response.versions);
        setSelectedId((current) => current || response.versions[0]?.version_id || "");
        setLoading(false);
      })
      .catch((loadError) => {
        if (!active) return;
        setError(loadError instanceof Error ? loadError.message : "Case versions could not be loaded.");
        setLoading(false);
      });
    return () => { active = false; };
  }, [caseId, connection]);

  useEffect(() => {
    if (!selectedId || connection !== "ready") return;
    let active = true;
    getCaseVersion(caseId, selectedId)
      .then((response) => { if (active) setSelected(response.version); })
      .catch((loadError) => { if (active) setError(loadError instanceof Error ? loadError.message : "The selected version could not be loaded."); });
    return () => { active = false; };
  }, [caseId, connection, selectedId]);

  const canSave = connection === "ready" && Boolean(workflow && evidenceReview && humanDecision);

  const saveCurrent = async () => {
    if (!workflow || !evidenceReview || !humanDecision || !canSave) return;
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const response = await saveCaseVersion({
        casePayload,
        rawExtraction,
        workflow,
        evidenceReview: JSON.parse(JSON.stringify(evidenceReview)) as Record<string, unknown>,
        humanDecision,
        parentVersionId: pendingUpdate?.baseVersionId || versions[0]?.version_id || null,
        trigger: pendingUpdate?.trigger || (versions.length ? "other" : "initial_board_review"),
        changeSummary: pendingUpdate?.changeSummary || (versions.length ? "Updated clinician or board decision package." : "Initial governed tumor-board review."),
      });
      setNotice(response.created ? `Version ${response.version.version_number} saved.` : `Version ${response.version.version_number} already contains this exact governed package.`);
      onVersionSaved(response.version);
      await loadVersions(response.version.version_id);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "The governed version could not be saved.");
    } finally {
      setSaving(false);
    }
  };

  const assess = async () => {
    if (!selected || !newValue.trim() || !documentId.trim() || !sourceExcerpt.trim() || !changeSummary.trim() || !attested) return;
    if (field === "performance_status") {
      const value = Number(newValue);
      if (!Number.isInteger(value) || value < 0 || value > 5) {
        setError("Performance status must be a whole ECOG value from 0 to 5.");
        return;
      }
    }
    setAssessing(true);
    setError("");
    setNotice("");
    try {
      const nextCase = buildUpdatedCase(selected.case, field, newValue, documentId, sourceExcerpt);
      const response = await assessCaseUpdate({
        baseVersionId: selected.version_id,
        updatedCase: nextCase,
        trigger,
        changeSummary,
        attested,
      });
      setProposedCase(nextCase);
      setAssessment(response);
    } catch (assessmentError) {
      setError(assessmentError instanceof Error ? assessmentError.message : "The update impact could not be assessed.");
    } finally {
      setAssessing(false);
    }
  };

  const apply = () => {
    if (!assessment || !proposedCase) return;
    onApplyUpdate({
      baseVersionId: assessment.base_version_id,
      updatedCase: proposedCase,
      trigger: assessment.trigger,
      changeSummary: assessment.change_summary,
      assessment,
    });
  };

  const selectedFinal = asRecord(selected?.workflow.result.final_decision);
  const selectedBoard = asRecord(selected?.human_decision.board_decision);

  return (
    <section className="version-workspace">
      <header className="version-workspace-header">
        <div>
          <p className="micro-label">Phase 8 · immutable case lineage</p>
          <h2>Versions and new information</h2>
          <p>Save complete governed snapshots, inspect what changed, and rerun only the specialist work affected by new information.</p>
        </div>
        <button className="secondary-button" type="button" onClick={onClose}>Return to case review</button>
      </header>

      {pendingUpdate && (
        <div className="pending-update-banner">
          <div><strong>Governed update in progress</strong><span>{pendingUpdate.changeSummary}</span></div>
          <p>Prior decisions remain historical. Re-commission evidence, run the targeted workflow, record the new human decision, then save the next version.</p>
        </div>
      )}

      <div className="version-control-bar">
        <div>
          <span>{versions.length}</span>
          <p><strong>saved versions</strong><small>Durable local SQLite lineage</small></p>
        </div>
        <div>
          <span>{workflow?.rerun ? workflow.rerun.specialist_agents_reused.length : 0}</span>
          <p><strong>specialist outputs reused</strong><small>Only when inputs were unchanged</small></p>
        </div>
        <button className="primary-button" type="button" disabled={!canSave || saving} onClick={() => void saveCurrent()}>
          {saving ? "Saving governed version…" : pendingUpdate ? "Save updated governed version" : "Save current governed version"}
        </button>
      </div>

      {!canSave && (
        <div className="version-prerequisite">
          <strong>A completed decision package is required before saving.</strong>
          <span>Finish evidence review, governed analysis, clinician judgment, and the board decision state first.</span>
        </div>
      )}
      {notice && <div className="version-notice" role="status">{notice}</div>}
      {error && <div className="decision-error" role="alert">{error}</div>}

      <nav className="version-view-tabs" aria-label="Version workspace views">
        <button type="button" aria-pressed={view === "history"} className={view === "history" ? "active" : ""} onClick={() => setView("history")}>Version history</button>
        <button type="button" aria-pressed={view === "update"} className={view === "update" ? "active" : ""} onClick={() => setView("update")} disabled={!versions.length}>Add new information</button>
      </nav>

      {view === "history" ? (
        <div className="version-history-layout">
          <aside className="version-timeline" aria-label="Saved case versions">
            {loading && <p>Loading saved versions…</p>}
            {!loading && versions.length === 0 && <div className="version-empty"><strong>No governed version saved yet</strong><p>Complete the Phase 7 decision package, then use the save action above.</p></div>}
            {versions.map((version) => (
              <button key={version.version_id} type="button" aria-current={selectedId === version.version_id ? "true" : undefined} className={selectedId === version.version_id ? "selected" : ""} onClick={() => setSelectedId(version.version_id)}>
                <span className="version-number">v{version.version_number}</span>
                <div><strong>{readable(version.trigger)}</strong><p>{version.change_summary}</p><small>{new Date(version.created_at).toLocaleString()}</small></div>
              </button>
            ))}
          </aside>
          <div className="version-detail-panel">
            {selected ? (
              <>
                <header><div><p className="micro-label">Immutable snapshot</p><h3>Version {selected.version_number}</h3></div><span>{selected.parent_version_id ? `Child of ${shortId(selected.parent_version_id)}` : "Root version"}</span></header>
                <div className="version-detail-metrics">
                  <div><span>Decision state</span><strong>{readable(selectedFinal.decision_state)}</strong></div>
                  <div><span>Board status</span><strong>{readable(selectedBoard.status)}</strong></div>
                  <div><span>Workflow</span><strong title={selected.workflow_request_id}>{shortId(selected.workflow_request_id)}</strong></div>
                  <div><span>Content hash</span><strong title={selected.content_hash}>{shortId(selected.content_hash)}</strong></div>
                </div>
                <article className="version-summary-card"><span>Why this version exists</span><p>{selected.change_summary}</p></article>
                <div className="version-lineage-note"><strong>Append-only record</strong><p>This snapshot cannot be overwritten. New information creates a child version and keeps this decision available as historical context.</p></div>
                <button className="secondary-button" type="button" onClick={() => setView("update")}>Start update from version {selected.version_number}</button>
              </>
            ) : <div className="version-empty"><strong>Select a saved version</strong><p>Its lineage, workflow, and human decision identifiers will appear here.</p></div>}
          </div>
        </div>
      ) : (
        <div className="new-information-layout">
          <div className="new-information-form">
            <div className="update-step-heading"><span>1</span><div><strong>Represent the new information</strong><p>The original saved version remains unchanged.</p></div></div>
            <div className="update-form-grid">
              <label><span>Base version</span><select value={selectedId} onChange={(event) => { setSelectedId(event.target.value); setAssessment(null); }}>
                {versions.map((version) => <option key={version.version_id} value={version.version_id}>Version {version.version_number} · {version.change_summary}</option>)}
              </select></label>
              <label><span>Update type</span><select value={trigger} onChange={(event) => setTrigger(event.target.value as CaseVersionTrigger)}>{triggerOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
              <label><span>Decision-critical field</span><select value={field} onChange={(event) => { setField(event.target.value as UpdateField); setAssessment(null); }}>{fieldOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
              <label><span>New represented value</span><input value={newValue} onChange={(event) => { setNewValue(event.target.value); setAssessment(null); }} placeholder={fieldOptions.find((item) => item.value === field)?.hint} /></label>
              <label><span>Source document ID</span><input value={documentId} onChange={(event) => { setDocumentId(event.target.value); setAssessment(null); }} /></label>
              <label className="full-update-field"><span>Exact source excerpt</span><textarea value={sourceExcerpt} onChange={(event) => { setSourceExcerpt(event.target.value); setAssessment(null); }} placeholder="Copy the exact sentence or result that supports this update." /></label>
              <label className="full-update-field"><span>Change summary</span><textarea value={changeSummary} onChange={(event) => { setChangeSummary(event.target.value); setAssessment(null); }} placeholder="Explain what changed and why the board package needs another review." /></label>
            </div>
            <label className="attestation-row"><input type="checkbox" checked={attested} onChange={(event) => { setAttested(event.target.checked); setAssessment(null); }} /><span>I attest that this update accurately represents the cited synthetic or fully de-identified source.</span></label>
            <button className="primary-button full-button" type="button" disabled={assessing || !selected || !newValue.trim() || !documentId.trim() || !sourceExcerpt.trim() || !changeSummary.trim() || !attested} onClick={() => void assess()}>{assessing ? "Assessing update impact…" : "Assess update impact"}</button>
          </div>

          <div className="update-impact-panel">
            <div className="update-step-heading"><span>2</span><div><strong>Review the rerun plan</strong><p>No prior decision is silently carried forward.</p></div></div>
            {assessment ? (
              <>
                <div className="impact-status"><span>{readable(assessment.change_severity)}</span><strong>{assessment.changed_paths.length} changed field path{assessment.changed_paths.length === 1 ? "" : "s"}</strong></div>
                <div className="impact-group"><span>Specialists that will run again</span><div>{assessment.specialist_agents_to_rerun.map((agent) => <strong key={agent}>{readable(agent)}</strong>)}</div></div>
                <div className="impact-group reusable"><span>Specialists eligible for reuse</span><div>{assessment.specialist_agents_eligible_for_reuse.map((agent) => <strong key={agent}>{readable(agent)}</strong>)}</div></div>
                <div className="impact-controls"><strong>Safety closure always reruns</strong><p>{assessment.always_rerun_controls.map((item) => readable(item)).join(" · ")}</p></div>
                <p className="impact-explanation">{assessment.explanation}</p>
                <button className="primary-button full-button" type="button" onClick={apply}>Apply update and re-commission evidence</button>
              </>
            ) : (
              <div className="version-empty"><strong>No impact plan yet</strong><p>Complete the source-linked update and select Assess update impact. The API will calculate which specialist work must run again.</p></div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
