"use client";

import { useEffect, useState } from "react";

import {
  type ApiConnectionState,
  type EvaluationSummary,
  type ReleaseReadiness,
  getEvaluationSummary,
  getReleaseReadiness,
} from "../lib/tumor-board-api";

function percent(value: number | null): string {
  return value === null ? "Baseline pending" : `${Math.round(value * 100)}%`;
}

const accessibilityControls = [
  "Keyboard-visible focus indicators",
  "Skip link to primary content",
  "Live connection and loading status",
  "Current workflow step announced",
  "Reduced-motion preference respected",
  "Errors announced as alerts",
];

export function EvaluationReleaseConsole({ connection }: { connection: ApiConnectionState }) {
  const [summary, setSummary] = useState<EvaluationSummary | null>(null);
  const [readiness, setReadiness] = useState<ReleaseReadiness | null>(null);
  const [error, setError] = useState("");
  const loading = connection === "ready" && !summary && !readiness && !error;

  useEffect(() => {
    let active = true;
    if (connection !== "ready") {
      return () => { active = false; };
    }
    Promise.all([getEvaluationSummary(), getReleaseReadiness()])
      .then(([evaluation, release]) => {
        if (!active) return;
        setSummary(evaluation);
        setReadiness(release);
      })
      .catch((reason: unknown) => {
        if (!active) return;
        setError(reason instanceof Error ? reason.message : "Phase 9 controls could not be loaded.");
      });
    return () => { active = false; };
  }, [connection]);

  const localChecks = readiness?.checks.filter((item) => item.level === "local_research") || [];
  const productionChecks = readiness?.checks.filter((item) => item.level === "production_research") || [];
  const clinicalChecks = readiness?.checks.filter((item) => item.level === "clinical_release") || [];

  return (
    <section className="release-console" aria-labelledby="release-console-title">
      <header className="release-console-header">
        <div>
          <p className="micro-label">Phase 9 evaluation and release controls</p>
          <h2 id="release-console-title">Research software release controls</h2>
          <p>Live software-governance measures are kept separate from clinical validation and authorization.</p>
        </div>
        <div className="release-state-strip" aria-label="Release states">
          <span className="ready">Local research ready</span>
          <span className={readiness?.production_research_ready ? "ready" : "blocked"}>
            {readiness?.production_research_ready ? "Production research ready" : "Production research blocked"}
          </span>
          <span className="blocked">Clinical release blocked</span>
        </div>
      </header>

      {loading && <div className="release-message" role="status" aria-live="polite">Loading evaluation and readiness controls from FastAPI…</div>}
      {!loading && (connection !== "ready" || error) && (
        <div className="release-message warning" role="alert">
          <strong>Live Phase 9 measures are unavailable</strong>
          <span>{error || "Start the local FastAPI service to load saved-version metrics and configuration checks."}</span>
        </div>
      )}

      <section className="release-section" aria-labelledby="primary-evaluation-title">
        <div className="release-section-heading">
          <div><p className="micro-label">Primary evaluation measures</p><h3 id="primary-evaluation-title">Three measures, each with a 100% target</h3></div>
          <span>{summary ? `${summary.versions_evaluated} saved version${summary.versions_evaluated === 1 ? "" : "s"}` : "Live baseline required"}</span>
        </div>
        <div className="evaluation-kpi-grid">
          {[
            ["critical_safety_gate_adherence", "Critical safety-gate adherence", "Every critical deterministic governance gate passes."],
            ["human_decision_separation", "Human-decision separation", "Stored human records preserve the original system synthesis."],
            ["evidence_attestation_completeness", "Evidence-attestation completeness", "Every admitted evidence set has a human attestation."],
          ].map(([id, label, explanation]) => {
            const metric = summary?.primary_metrics.find((item) => item.metric_id === id);
            return (
              <article className="evaluation-kpi" key={id}>
                <span>{label}</span>
                <strong>{percent(metric?.value ?? null)}</strong>
                <small>Target 100% · {metric ? `${metric.numerator}/${metric.denominator}` : "no live denominator"}</small>
                <p>{explanation}</p>
              </article>
            );
          })}
        </div>
      </section>

      <section className="release-section guardrail-section" aria-labelledby="guardrail-title">
        <div className="release-section-heading">
          <div><p className="micro-label">Zero-tolerance guardrails</p><h3 id="guardrail-title">A single violation requires review</h3></div>
          <span>Target 0</span>
        </div>
        <div className="guardrail-grid">
          {[
            ["unsafe_render_violations", "Unsafe render violations"],
            ["decision_lineage_violations", "Decision-lineage violations"],
            ["unaudited_specialist_reuse_violations", "Unaudited specialist reuse"],
          ].map(([id, label]) => {
            const metric = summary?.guardrails.find((item) => item.metric_id === id);
            return <article key={id}><span>{label}</span><strong>{metric?.value ?? "Pending"}</strong><small>Zero tolerance</small></article>;
          })}
        </div>
      </section>

      <section className="release-section" aria-labelledby="readiness-title">
        <div className="release-section-heading">
          <div><p className="micro-label">Readiness checklist</p><h3 id="readiness-title">Three levels that must not be confused</h3></div>
          <span>Configuration-backed</span>
        </div>
        <div className="readiness-columns">
          {[
            ["Local software", localChecks, "local"],
            ["Production research", productionChecks, "production"],
            ["Clinical governance", clinicalChecks, "clinical"],
          ].map(([label, checks, tone]) => (
            <article className={`readiness-column ${tone}`} key={String(label)}>
              <h4>{String(label)}</h4>
              {(checks as typeof localChecks).length ? (checks as typeof localChecks).map((check) => (
                <div className="readiness-check" key={check.check_id}>
                  <span className={check.status}>{check.status === "ready" ? "✓" : "!"}</span>
                  <div><strong>{check.check_id.replaceAll("_", " ")}</strong><p>{check.detail}</p>{check.status !== "ready" && <small>{check.remediation}</small>}</div>
                </div>
              )) : <p className="readiness-empty">Connect FastAPI to inspect the live checklist.</p>}
            </article>
          ))}
        </div>
      </section>

      <div className="release-lower-grid">
        <section className="release-section accessibility-card" aria-labelledby="accessibility-title">
          <p className="micro-label">Accessibility implementation</p>
          <h3 id="accessibility-title">Built into the workspace</h3>
          <div className="accessibility-checklist">
            {accessibilityControls.map((control) => <span key={control}><i aria-hidden="true">✓</i>{control}</span>)}
          </div>
        </section>
        <section className="release-section limits-card" aria-labelledby="limits-title">
          <p className="micro-label">Evaluation limits</p>
          <h3 id="limits-title">What these measures do not prove</h3>
          <p>They do not measure clinical correctness, patient outcome benefit, model calibration, subgroup fairness, external validity, or site-specific safety.</p>
          <strong>Passing Phase 9 is a software milestone, never a clinical authorization.</strong>
        </section>
      </div>
    </section>
  );
}
