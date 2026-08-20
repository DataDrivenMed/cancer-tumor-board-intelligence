"use client";

import { useMemo, useState } from "react";

import { localEvidenceFixture } from "../data/evidence-fixture";
import {
  type ApiConnectionState,
  type EvidenceCandidate,
  type EvidenceCandidateSetResponse,
  type EvidenceChannel,
  type EvidenceDecision,
  type EvidenceMode,
  getEvidenceCandidates,
} from "../lib/tumor-board-api";

type EvidenceView = EvidenceChannel | "downstream";

export interface EvidenceReviewEvent {
  id: string;
  timestamp: string;
  action: "candidate_set_loaded" | "candidate_approved" | "candidate_rejected" | "commission_saved";
  detail: string;
}

export interface CommissionedEvidenceReview {
  mode: EvidenceMode;
  candidateSetId: string;
  decisions: EvidenceDecision[];
  attested: boolean;
  candidates: EvidenceCandidate[];
  warnings: string[];
  downstreamChannels: Record<string, unknown>[];
  events: EvidenceReviewEvent[];
  validatedByApi: boolean;
}

interface Props {
  casePayload: Record<string, unknown>;
  connection: ApiConnectionState;
  initialCommission: CommissionedEvidenceReview | null;
  onDirty: () => void;
  onCommissioned: (review: CommissionedEvidenceReview) => void;
}

const channelLabels: Record<EvidenceView, string> = {
  guideline: "Formal guidance",
  molecular: "Molecular",
  safety: "Safety",
  downstream: "Downstream discovery",
};

function event(action: EvidenceReviewEvent["action"], detail: string): EvidenceReviewEvent {
  return {
    id: `${action}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    timestamp: new Date().toISOString(),
    action,
    detail,
  };
}

export function EvidenceCommissioningReview({
  casePayload,
  connection,
  initialCommission,
  onDirty,
  onCommissioned,
}: Props) {
  const [mode, setMode] = useState<EvidenceMode>(initialCommission?.mode || "guided_fixture");
  const [candidateSet, setCandidateSet] = useState<EvidenceCandidateSetResponse | null>(() =>
    initialCommission
      ? {
          request_id: "restored-local-review",
          api_version: "0.6.0",
          case_id: String(casePayload.case_id || "TBI-AML-042"),
          research_use_only: true,
          mode: initialCommission.mode,
          candidate_set_id: initialCommission.candidateSetId,
          candidates: initialCommission.candidates,
          downstream_channels: initialCommission.downstreamChannels,
          warnings: initialCommission.warnings,
        }
      : null,
  );
  const [decisions, setDecisions] = useState<Record<string, EvidenceDecision>>(() =>
    Object.fromEntries((initialCommission?.decisions || []).map((item) => [item.candidate_id, item])),
  );
  const [attested, setAttested] = useState(initialCommission?.attested || false);
  const [activeChannel, setActiveChannel] = useState<EvidenceView>("guideline");
  const [events, setEvents] = useState<EvidenceReviewEvent[]>(initialCommission?.events || []);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const candidates = useMemo(() => candidateSet?.candidates || [], [candidateSet]);
  const selectedCandidates = candidates.filter((candidate) => candidate.channel === activeChannel);
  const decisionList = Object.values(decisions);
  const approvedCount = decisionList.filter((item) => item.decision === "approved").length;
  const rejectedCount = decisionList.filter((item) => item.decision === "rejected").length;
  const isComplete = candidates.length > 0 && candidates.every((candidate) => {
    const item = decisions[candidate.candidate_id];
    return Boolean(item && (item.decision === "approved" || (item.decision === "rejected" && item.reason.trim())));
  });
  const hasApprovals = approvedCount > 0;
  const canSave = isComplete && (!hasApprovals || attested);
  const validatedByApi = (candidateSet?.candidate_set_id.length || 0) === 64;

  const counts = useMemo(() => ({
    guideline: candidates.filter((item) => item.channel === "guideline").length,
    molecular: candidates.filter((item) => item.channel === "molecular").length,
    safety: candidates.filter((item) => item.channel === "safety").length,
  }), [candidates]);

  const chooseMode = (nextMode: EvidenceMode) => {
    if (nextMode === mode) return;
    setMode(nextMode);
    setCandidateSet(null);
    setDecisions({});
    setAttested(false);
    setEvents([]);
    setError("");
    onDirty();
  };

  const loadCandidates = async () => {
    setLoading(true);
    setError("");
    onDirty();
    try {
      if (connection !== "ready" && mode === "live") {
        throw new Error("Live retrieval requires the local FastAPI service. Choose Guided for a visual preview or reconnect the service.");
      }
      const response = connection === "ready"
        ? await getEvidenceCandidates(casePayload, mode)
        : localEvidenceFixture;
      const nextEvents = [event(
        "candidate_set_loaded",
        response.candidate_set_id
          ? `${response.candidates.length} case-bound candidates retrieved from FastAPI.`
          : `${response.candidates.length} local preview candidates loaded. API validation is still required.`,
      )];
      setCandidateSet(response);
      setDecisions({});
      setAttested(false);
      setEvents(nextEvents);
      setActiveChannel("guideline");
    } catch (candidateError) {
      setError(candidateError instanceof Error ? candidateError.message : "Evidence candidates could not be retrieved.");
    } finally {
      setLoading(false);
    }
  };

  const setDecision = (candidate: EvidenceCandidate, decision: EvidenceDecision["decision"]) => {
    if (candidate.synthetic && decision === "approved") return;
    onDirty();
    const next = {
      candidate_id: candidate.candidate_id,
      decision,
      reason: decision === "rejected" ? decisions[candidate.candidate_id]?.reason || "" : "",
    };
    setDecisions((current) => ({ ...current, [candidate.candidate_id]: next }));
    setEvents((current) => [...current, event(
      decision === "approved" ? "candidate_approved" : "candidate_rejected",
      `${candidate.title} marked ${decision}.`,
    )]);
  };

  const updateReason = (candidateId: string, reason: string) => {
    onDirty();
    setDecisions((current) => ({
      ...current,
      [candidateId]: { candidate_id: candidateId, decision: "rejected", reason },
    }));
  };

  const saveCommission = () => {
    if (!candidateSet || !canSave) return;
    const saveEvent = event(
      "commission_saved",
      `${approvedCount} candidates approved and ${rejectedCount} rejected. ${validatedByApi ? "Candidate set validated by FastAPI." : "Local preview saved; API validation remains required."}`,
    );
    const nextEvents = [...events, saveEvent];
    setEvents(nextEvents);
    onCommissioned({
      mode,
      candidateSetId: candidateSet.candidate_set_id,
      decisions: candidates.map((candidate) => decisions[candidate.candidate_id]!),
      attested,
      candidates,
      warnings: candidateSet.warnings,
      downstreamChannels: candidateSet.downstream_channels,
      events: nextEvents,
      validatedByApi,
    });
  };

  return (
    <div className="evidence-workbench">
      <section className="editorial-card evidence-commission-header">
        <div>
          <p className="micro-label">Phase 5 control point</p>
          <h3>Governed evidence commissioning</h3>
          <p>No evidence candidate enters analysis until a clinician approves or rejects it. Every rejection needs a reason, and every approval needs an attestation.</p>
        </div>
        <div className="evidence-mode-panel" aria-label="Evidence retrieval mode">
          <span>Retrieval mode</span>
          <div>
            <button type="button" className={mode === "guided_fixture" ? "active" : ""} onClick={() => chooseMode("guided_fixture")}>Guided</button>
            <button type="button" className={mode === "live" ? "active" : ""} onClick={() => chooseMode("live")}>Live sources</button>
          </div>
          <small>{mode === "guided_fixture" ? "Safe demonstration with controlled fixtures" : "Retrieve current CIViC and FDA candidates"}</small>
        </div>
        <button className="primary-button" type="button" onClick={() => void loadCandidates()} disabled={loading}>
          {loading ? "Retrieving candidates…" : candidateSet ? "Refresh candidate set" : "Retrieve evidence candidates"}
        </button>
      </section>

      {error && <div className="workflow-error" role="alert"><strong>Candidate retrieval stopped</strong><span>{error}</span><button type="button" onClick={() => void loadCandidates()}>Retry</button></div>}

      {!candidateSet ? (
        <section className="editorial-card evidence-start-state">
          <span className="evidence-step-number">1</span>
          <div><h3>Start by retrieving the case-bound candidate set</h3><p>The system will assemble guidance, molecular, and safety records for review. Retrieval is discovery only. You decide what is admitted.</p></div>
        </section>
      ) : (
        <>
          <section className="evidence-review-summary" aria-label="Evidence review progress">
            <div><strong>{candidates.length}</strong><span>candidates</span></div>
            <div><strong>{approvedCount}</strong><span>approved</span></div>
            <div><strong>{rejectedCount}</strong><span>rejected</span></div>
            <div><strong>{candidates.length - decisionList.length}</strong><span>awaiting review</span></div>
            <div className={validatedByApi ? "validated" : "preview"}><strong>{validatedByApi ? "API" : "Local"}</strong><span>{validatedByApi ? "validated set" : "visual preview"}</span></div>
          </section>

          {candidateSet.warnings.map((warning) => <div className="evidence-warning" key={warning}><strong>Evidence boundary</strong><span>{warning}</span></div>)}

          <nav className="evidence-channel-tabs" aria-label="Evidence channels">
            {(Object.keys(channelLabels) as EvidenceView[]).map((channel) => (
              <button type="button" key={channel} className={activeChannel === channel ? "active" : ""} onClick={() => setActiveChannel(channel)}>
                <span>{channelLabels[channel]}</span>
                <small>{channel === "downstream" ? candidateSet.downstream_channels.length : counts[channel]}</small>
              </button>
            ))}
          </nav>

          {activeChannel === "downstream" ? (
            <section className="downstream-grid">
              {candidateSet.downstream_channels.map((item, index) => (
                <article className="editorial-card downstream-card" key={`${String(item.channel)}-${index}`}>
                  <p className="micro-label">Downstream governed channel</p>
                  <h3>{String(item.channel || "Additional evidence")}</h3>
                  <strong>{String(item.mode || "Governed retrieval")}</strong>
                  <p>{String(item.boundary || "Independent verification is required before clinical use.")}</p>
                </article>
              ))}
            </section>
          ) : (
            <div className="evidence-candidate-list">
              {selectedCandidates.length === 0 && <section className="editorial-card connected-empty-state"><h3>No candidates returned for this channel</h3><p>The empty result remains visible and no source is invented.</p></section>}
              {selectedCandidates.map((candidate) => {
                const current = decisions[candidate.candidate_id];
                return (
                  <article className={`editorial-card evidence-candidate ${current?.decision || "unreviewed"}`} key={candidate.candidate_id}>
                    <header>
                      <div>
                        <div className="candidate-labels">
                          <span>{candidate.source_type.replaceAll("_", " ")}</span>
                          <span>{candidate.verification_status.replaceAll("_", " ")}</span>
                          {candidate.synthetic && <span className="synthetic-label">Controlled fixture</span>}
                        </div>
                        <h3>{candidate.title}</h3>
                        <p>{candidate.source_organization} · {candidate.source_date || "Date not represented"}</p>
                      </div>
                      <span className={`decision-state ${current?.decision || "unreviewed"}`}>{current?.decision || "Awaiting decision"}</span>
                    </header>

                    <div className="candidate-body">
                      <div>
                        <p className="micro-label">Why it was retrieved</p>
                        <p>{candidate.summary}</p>
                      </div>
                      <blockquote>
                        <span>Exact source excerpt</span>
                        <p>“{candidate.exact_excerpt}”</p>
                        <cite>{candidate.source_title} · {candidate.source_locator}</cite>
                      </blockquote>
                    </div>

                    <footer>
                      <a href={candidate.source_url} target="_blank" rel="noreferrer">Open source record</a>
                      <div className="candidate-actions">
                        <button type="button" className={current?.decision === "approved" ? "selected approve" : "approve"} disabled={candidate.synthetic} title={candidate.synthetic ? "Controlled fixtures cannot be approved for production reasoning." : undefined} onClick={() => setDecision(candidate, "approved")}>Approve for analysis</button>
                        <button type="button" className={current?.decision === "rejected" ? "selected reject" : "reject"} onClick={() => setDecision(candidate, "rejected")}>Reject with reason</button>
                      </div>
                    </footer>

                    {candidate.synthetic && <p className="fixture-boundary">Controlled fixtures must be rejected. Production agents also exclude them even if a request is tampered with.</p>}
                    {current?.decision === "rejected" && (
                      <label className="rejection-reason">
                        Rejection reason
                        <textarea value={current.reason} onChange={(change) => updateReason(candidate.candidate_id, change.target.value)} placeholder="Explain why this candidate must not enter analysis." />
                      </label>
                    )}
                  </article>
                );
              })}
            </div>
          )}

          <section className={`editorial-card evidence-attestation ${canSave ? "ready" : ""}`}>
            <div>
              <p className="micro-label">Human evidence attestation</p>
              <h3>Commission the reviewed evidence set</h3>
              <p>{isComplete ? "Every candidate has a recorded decision." : "Review every candidate and provide a reason for each rejection."} {validatedByApi ? "FastAPI will revalidate this exact candidate set before analysis." : "This local visual preview must be retrieved again after FastAPI reconnects before analysis can run."}</p>
            </div>
            <label>
              <input type="checkbox" checked={attested} onChange={(change) => { setAttested(change.target.checked); onDirty(); }} />
              I reviewed the exact excerpts and source locators for every approved candidate.
            </label>
            <button className="primary-button" type="button" disabled={!canSave} onClick={saveCommission}>Save evidence decisions</button>
          </section>
        </>
      )}
    </div>
  );
}
