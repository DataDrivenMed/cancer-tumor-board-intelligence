"use client";

import { useState } from "react";

import type { WorkflowRunResponse } from "../lib/tumor-board-api";

type AnalysisView = "overview" | "channels" | "challenge" | "synthesis";

interface Props {
  workflow: WorkflowRunResponse | null;
  evidenceReady: boolean;
  running: boolean;
  onRun: () => void;
}

interface ChannelDefinition {
  id: string;
  label: string;
  purpose: string;
  claimGate: string;
  countKey: string;
  countLabel: string;
}

const channelDefinitions: ChannelDefinition[] = [
  { id: "guideline", label: "Formal guidance", purpose: "Management framework", claimGate: "can_support_guideline_claim", countKey: "matched_guidance", countLabel: "matched statements" },
  { id: "molecular", label: "Molecular evidence", purpose: "Bounded clinical actionability", claimGate: "can_support_clinical_actionability_claim", countKey: "interpretations", countLabel: "interpretations" },
  { id: "literature", label: "Current literature", purpose: "Question-specific context", claimGate: "can_support_literature_claim", countKey: "articles", countLabel: "verified articles" },
  { id: "clinical_trials", label: "Clinical trials", purpose: "Possible matches, never eligibility", claimGate: "can_support_trial_match_claim", countKey: "matches", countLabel: "possible matches" },
  { id: "safety", label: "Safety evidence", purpose: "Hazards, exclusions, and monitoring", claimGate: "can_support_safety_claim", countKey: "findings", countLabel: "safety findings" },
  { id: "translational", label: "Translational evidence", purpose: "Mechanistic context only", claimGate: "can_support_mechanistic_claim", countKey: "findings", countLabel: "mechanistic findings" },
];

const viewLabels: Record<AnalysisView, string> = {
  overview: "Decision gate",
  channels: "Evidence channels",
  challenge: "Clinical Red Team",
  synthesis: "Governed synthesis",
};

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
}

function asRecords(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value) ? value.map(asRecord) : [];
}

function asStrings(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string" && Boolean(item.trim())) : [];
}

function readable(value: unknown, fallback = "Not represented"): string {
  if (typeof value === "string" && value.trim()) return value.replaceAll("_", " ");
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return fallback;
}

function statusTone(status: string): "verified" | "attention" | "limited" | "neutral" {
  if (status === "completed") return "verified";
  if (status === "completed_with_limitations" || status === "no_evidence_found") return "attention";
  if (["source_unavailable", "verification_failed", "tool_failure", "schema_error", "escalate_human"].includes(status)) return "limited";
  return "neutral";
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    completed: "Available",
    completed_with_limitations: "Available with limits",
    no_evidence_found: "No bounded result",
    source_unavailable: "Source unavailable",
    verification_failed: "Verification failed",
    insufficient_input: "More information needed",
    tool_failure: "Retrieval failed",
    escalate_human: "Human review required",
  };
  return labels[status] || readable(status, "Not returned");
}

function Status({ tone, children }: { tone: string; children: React.ReactNode }) {
  return <span className={`status-pill ${tone}`}>{children}</span>;
}

function CandidateCard({ candidate, index }: { candidate: Record<string, unknown>; index: number }) {
  const conditions = asStrings(candidate.conditions);
  const exclusions = asStrings(candidate.exclusions);
  return (
    <article className="analysis-candidate-card">
      <header>
        <span>{String(index + 1).padStart(2, "0")}</span>
        <div><p className="micro-label">Evidence-anchored strategy</p><h4>{readable(candidate.strategy)}</h4></div>
        <Status tone="attention">Conditional</Status>
      </header>
      <blockquote><span>Exact supporting excerpt</span><p>“{readable(candidate.source_excerpt)}”</p><cite>{readable(candidate.source_locator, "Source locator not represented")}</cite></blockquote>
      <div className="candidate-conditions">
        <div><strong>Conditions to verify</strong>{conditions.length ? <ul>{conditions.map((item) => <li key={item}>{item}</li>)}</ul> : <p>No additional conditions returned.</p>}</div>
        <div><strong>Exclusions and boundaries</strong>{exclusions.length ? <ul>{exclusions.map((item) => <li key={item}>{item}</li>)}</ul> : <p>No exclusions returned.</p>}</div>
      </div>
    </article>
  );
}

export function GovernedAnalysisReview({ workflow, evidenceReady, running, onRun }: Props) {
  const [view, setView] = useState<AnalysisView>("overview");
  const [expandedChannel, setExpandedChannel] = useState<string | null>(null);

  const result = asRecord(workflow?.result);
  const routing = asRecord(result.routing);
  const outputs = asRecord(result.specialist_outputs);
  const redTeam = asRecord(result.red_team_report);
  const consensus = asRecord(result.consensus_report);
  const finalDecision = asRecord(result.final_decision);
  const findings = asRecords(redTeam.findings).length ? asRecords(redTeam.findings) : asRecords(result.red_team_findings);
  const channels = asRecords(consensus.evidence_channels);
  const candidates = asRecords(consensus.candidates);
  const decisionState = readable(finalDecision.decision_state, "not run");
  const abstained = decisionState === "abstain";
  const safeToRender = consensus.safe_to_render_decision_support === true;
  const discussionPriorities = asStrings(finalDecision.discussion_priorities);
  const uncertainties = asStrings(finalDecision.major_uncertainties);
  const selectedReviews = asStrings(routing.selected_agents);

  const channelRows = channelDefinitions.map((definition) => {
    const output = asRecord(outputs[definition.id]);
    const consensusChannel = channels.find((channel) => channel.agent_id === definition.id) || {};
    const status = readable(output.status, "not_selected").replaceAll(" ", "_");
    const records = asRecords(output[definition.countKey]);
    return {
      ...definition,
      output,
      consensusChannel,
      status,
      records,
      claimSupported: output[definition.claimGate] === true,
      summary: readable(output.summary, "This channel was not selected or returned no summary."),
      limitations: asStrings(output.limitations),
      warnings: asStrings(output.warnings),
    };
  });

  if (!workflow) {
    return (
      <div className="analysis-empty-workbench">
        <section className="editorial-card analysis-readiness-card">
          <div><p className="micro-label">Phase 6 analysis gate</p><h3>Run only after the evidence set is commissioned</h3><p>The workflow will verify the case, route bounded specialist reviews, challenge the evidence package, and then either provide conditional decision support or abstain with clear next actions.</p></div>
          <div className="analysis-readiness-steps">
            <span className={evidenceReady ? "complete" : ""}><i>1</i><strong>Evidence commissioned</strong><small>{evidenceReady ? "FastAPI-validated set ready" : "Complete Phase 5 first"}</small></span>
            <span><i>2</i><strong>Challenge the evidence</strong><small>Independent structural and safety checks</small></span>
            <span><i>3</i><strong>Apply the synthesis gate</strong><small>No voting and no unsupported ranking</small></span>
          </div>
          <button className="primary-button" type="button" disabled={!evidenceReady || running} onClick={onRun}>{running ? "Running governed analysis…" : evidenceReady ? "Run governed analysis" : "Commission evidence first"}</button>
        </section>
        <section className="analysis-principle-grid">
          <article><strong>No source substitution</strong><p>An unavailable governed source cannot be replaced with model memory.</p></article>
          <article><strong>Challenge before synthesis</strong><p>The Clinical Red Team can block downstream decision support.</p></article>
          <article><strong>Useful abstention</strong><p>A stopped workflow explains why it stopped and what should happen next.</p></article>
        </section>
      </div>
    );
  }

  return (
    <div className="analysis-workbench">
      <section className={`analysis-decision-banner ${abstained ? "withheld" : "conditional"}`}>
        <div className="analysis-decision-symbol" aria-hidden="true">{abstained ? "!" : "✓"}</div>
        <div>
          <p className="micro-label">Governed decision state</p>
          <h3>{abstained ? "Management synthesis withheld safely" : "Conditional decision support available"}</h3>
          <p>{readable(finalDecision.abstention_reason, readable(consensus.summary, "The governed analysis completed with explicit evidence boundaries."))}</p>
        </div>
        <div className="analysis-decision-meta">
          <span><small>Decision state</small><strong>{decisionState}</strong></span>
          <span><small>Support strength</small><strong>{readable(finalDecision.decision_support_strength, "insufficient")}</strong></span>
          <span><small>Safe to render options</small><strong>{safeToRender ? "Yes" : "No"}</strong></span>
        </div>
      </section>

      <section className="analysis-flow-strip" aria-label="Governed analysis progression">
        <div className="complete"><span>01</span><p>Specialist routing<strong>{selectedReviews.length} bounded reviews</strong></p></div>
        <div className={readable(redTeam.disposition) === "blocked" ? "blocked" : "complete"}><span>02</span><p>Clinical Red Team<strong>{readable(redTeam.disposition, "not returned")}</strong></p></div>
        <div className={abstained ? "blocked" : "complete"}><span>03</span><p>Consensus gate<strong>{readable(consensus.disposition, "not returned")}</strong></p></div>
      </section>

      <nav className="analysis-view-tabs" aria-label="Analysis views">
        {(Object.keys(viewLabels) as AnalysisView[]).map((item) => <button type="button" key={item} className={view === item ? "active" : ""} onClick={() => setView(item)}>{viewLabels[item]}</button>)}
      </nav>

      {view === "overview" && (
        <div className="analysis-overview-grid">
          <section className="editorial-card next-action-card">
            <div className="card-heading-row"><div><p className="micro-label">What happens next</p><h3>{abstained ? "Resolve the blockers before relying on synthesis" : "Review the conditions before board discussion"}</h3></div><Status tone={abstained ? "limited" : "attention"}>{discussionPriorities.length} actions</Status></div>
            {discussionPriorities.length ? <ol>{discussionPriorities.map((priority, index) => <li key={`${priority}-${index}`}><span>{String(index + 1).padStart(2, "0")}</span><p>{priority}</p></li>)}</ol> : <p className="supporting-copy">No additional discussion priorities were returned.</p>}
          </section>
          <section className="editorial-card analysis-channel-summary">
            <div className="card-heading-row"><div><p className="micro-label">Evidence contribution</p><h3>What each channel could support</h3></div><Status tone="neutral">No agent voting</Status></div>
            <div className="channel-summary-list">
              {channelRows.map((channel) => <div key={channel.id}><span className={`source-dot ${channel.claimSupported ? "ready" : "limited"}`} /><p><strong>{channel.label}</strong><small>{channel.claimSupported ? "Bounded claim support available" : statusLabel(channel.status)}</small></p></div>)}
            </div>
          </section>
          <section className="editorial-card red-team-summary-card">
            <div><p className="micro-label">Independent challenge</p><h3>{readable(redTeam.summary, findings.length ? `${findings.length} challenge findings recorded` : "No deterministic challenge findings")}</h3></div>
            <div className="red-team-metrics"><span><strong>{readable(redTeam.critical_count, String(findings.filter((item) => item.severity === "critical").length))}</strong><small>critical</small></span><span><strong>{readable(redTeam.blocking_count, String(findings.filter((item) => item.recommendation_blocking === true).length))}</strong><small>blocking</small></span><span><strong>{readable(redTeam.safe_for_consensus, "false")}</strong><small>safe for consensus</small></span></div>
            <button type="button" className="secondary-button" onClick={() => setView("challenge")}>Inspect challenge findings</button>
          </section>
        </div>
      )}

      {view === "channels" && (
        <div className="analysis-channel-list">
          {channelRows.map((channel) => {
            const expanded = expandedChannel === channel.id;
            const consensusState = readable(channel.consensusChannel.state, channel.claimSupported ? "supportive" : "limiting");
            return (
              <article className={`editorial-card analysis-channel-card ${channel.claimSupported ? "supportive" : "limited"}`} key={channel.id}>
                <header>
                  <div><p className="micro-label">{channel.purpose}</p><h3>{channel.label}</h3></div>
                  <div><Status tone={statusTone(channel.status)}>{statusLabel(channel.status)}</Status><Status tone={channel.claimSupported ? "verified" : "neutral"}>{consensusState}</Status></div>
                </header>
                <p className="channel-summary">{channel.summary}</p>
                <div className="channel-claim-row"><span><strong>{channel.records.length}</strong><small>{channel.countLabel}</small></span><p><strong>Claim boundary</strong>{channel.claimSupported ? "This channel can support its defined bounded claim." : "This channel cannot support its defined claim in this request."}</p></div>
                <button type="button" className="channel-expand-button" aria-expanded={expanded} onClick={() => setExpandedChannel(expanded ? null : channel.id)}>{expanded ? "Hide source-bound detail" : "Inspect source-bound detail"}</button>
                {expanded && <div className="channel-detail-panel">
                  {channel.id === "guideline" && channel.records.map((record, index) => <blockquote key={`${readable(record.recommendation_id)}-${index}`}><span>Verified guidance excerpt</span><p>“{readable(record.source_excerpt)}”</p><cite>{readable(record.source_title)} · {readable(record.source_locator)}</cite></blockquote>)}
                  {channel.id === "clinical_trials" && channel.records.slice(0, 4).map((record) => <div className="trial-analysis-row" key={readable(record.nct_id)}><p><strong>{readable(record.nct_id)}</strong><span>{readable(record.title)}</span></p><Status tone="attention">Possible match only</Status></div>)}
                  {!channel.records.length && <p className="channel-empty-detail">No verified records are available to display. Nothing has been generated to fill the gap.</p>}
                  {(channel.limitations.length > 0 || channel.warnings.length > 0) && <div className="channel-boundaries"><strong>Limitations and warnings</strong><ul>{[...channel.limitations, ...channel.warnings].map((item) => <li key={item}>{item}</li>)}</ul></div>}
                </div>}
              </article>
            );
          })}
        </div>
      )}

      {view === "challenge" && (
        <section className="editorial-card challenge-workbench">
          <div className="card-heading-row"><div><p className="micro-label">Clinical Red Team</p><h3>Independent pre-synthesis challenge</h3><p>The challenger checks evidence promotion, missing prerequisites, conflicts, availability failures, and safety gates. It does not invent an alternative treatment.</p></div><Status tone={findings.length ? "limited" : "verified"}>{readable(redTeam.disposition, findings.length ? "challenged" : "clear")}</Status></div>
          {findings.length ? <div className="challenge-finding-list">{findings.map((finding, index) => <article key={`${readable(finding.code, readable(finding.category))}-${index}`}>
            <div className="challenge-index"><span>{String(index + 1).padStart(2, "0")}</span><Status tone={finding.severity === "critical" ? "limited" : "attention"}>{readable(finding.severity)}</Status></div>
            <div><p className="micro-label">{readable(finding.category)}</p><h4>{readable(finding.issue)}</h4><p>{readable(finding.effect_on_recommendation)}</p>{finding.recommendation_blocking === true && <strong className="blocking-label">Recommendation blocking</strong>}</div>
          </article>)}</div> : <div className="challenge-clear-state"><span>✓</span><div><h4>No deterministic challenge findings</h4><p>A clear structural challenge does not establish treatment correctness or patient safety. Human tumor-board judgment remains required.</p></div></div>}
          {asStrings(redTeam.limitations).length > 0 && <div className="red-team-boundary"><strong>What this review does not establish</strong><ul>{asStrings(redTeam.limitations).map((item) => <li key={item}>{item}</li>)}</ul></div>}
        </section>
      )}

      {view === "synthesis" && (
        <div className="synthesis-workbench">
          <section className="editorial-card synthesis-rule-card">
            <div><p className="micro-label">Consensus rule</p><h3>Evidence is integrated by permission, not popularity</h3><p>Only verified formal or consensus guidance can anchor an explicit management candidate. Other channels may contextualize, constrain, or block that candidate within their own claim boundaries.</p></div>
            <div className="synthesis-rule-flow"><span>Verified guidance<small>May anchor a candidate</small></span><i>+</i><span>Bounded channels<small>Context, constraints, blocks</small></span><i>→</i><span className={safeToRender ? "allowed" : "withheld"}>{safeToRender ? "Conditional options" : "Abstention"}<small>{safeToRender ? "Human adjudication required" : "Unsupported output withheld"}</small></span></div>
          </section>
          {safeToRender && candidates.length ? <div className="analysis-candidate-list">{candidates.map((candidate, index) => <CandidateCard candidate={candidate} index={index} key={readable(candidate.candidate_id, String(index))} />)}</div> : <section className="editorial-card abstention-action-card"><span className="abstention-mark">!</span><div><p className="micro-label">Useful abstention</p><h3>No management option is rendered from the current evidence package</h3><p>{readable(consensus.summary, readable(finalDecision.abstention_reason))}</p><strong>What could change this state</strong>{discussionPriorities.length ? <ul>{discussionPriorities.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul> : <p>No next actions were returned.</p>}</div></section>}
          {uncertainties.length > 0 && <section className="editorial-card uncertainty-card"><p className="micro-label">Major uncertainties</p><h3>Keep these visible in board discussion</h3><ul>{uncertainties.map((item) => <li key={item}>{item}</li>)}</ul></section>}
        </div>
      )}
    </div>
  );
}
