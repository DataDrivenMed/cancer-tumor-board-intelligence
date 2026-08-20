"use client";

import { useEffect, useState } from "react";

import {
  listProductCases,
  type CaseVersionSummary,
} from "../lib/tumor-board-api";

type Props = {
  connection: "checking" | "ready" | "unavailable";
  syntheticOnly?: boolean;
  onStartSynthetic: () => void;
  onStartDeidentified: () => void;
  onOpenCase: (caseItem: CaseVersionSummary) => void;
};

export function ProductHome({ connection, syntheticOnly = false, onStartSynthetic, onStartDeidentified, onOpenCase }: Props) {
  const [cases, setCases] = useState<CaseVersionSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    listProductCases()
      .then((response) => { if (active) setCases(response.cases); })
      .catch(() => { if (active) setCases([]); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  return (
    <main className="product-home" id="main-content" tabIndex={-1}>
      <section className="product-hero">
        <div>
          <p className="micro-label">{syntheticOnly ? "Synthetic faculty evaluation" : "Private clinician workspace"}</p>
          <h1>{syntheticOnly ? "Explore a complete governed tumor-board workflow" : "Start safely, then build a board-ready case"}</h1>
          <p>{syntheticOnly ? "Use the controlled AML teaching case to evaluate source review, evidence governance, AI analysis, human judgment, and auditability without patient data." : "Learn the workflow with a synthetic case, or begin a real case only after the source has been de-identified."}</p>
        </div>
        <span className={`connection-status ${connection}`}><i aria-hidden="true" />{connection === "ready" ? (syntheticOnly ? "Evaluation service ready" : "Clinical service ready") : connection === "checking" ? "Checking service" : "Service unavailable"}</span>
      </section>

      <section className={`start-paths ${syntheticOnly ? "single-path" : ""}`} aria-label="Start a case">
        <article className="start-path synthetic-path">
          <span className="path-number">01</span>
          <p className="micro-label">Recommended first</p>
          <h2>Learn with the synthetic case</h2>
          <p>A complete AML teaching packet demonstrates source review, governed evidence, AI analysis, human judgment, and version history without patient data.</p>
          <button type="button" className="primary-button" onClick={onStartSynthetic}>Open guided synthetic case</button>
        </article>
        {!syntheticOnly && <article className="start-path clinical-path">
          <span className="path-number">02</span>
          <p className="micro-label">For authorized users</p>
          <h2>Start a de-identified case</h2>
          <p>Upload a source that your organization has already de-identified. The product performs a secondary identifier screen and does not retain the original file.</p>
          <button type="button" className="secondary-button" onClick={onStartDeidentified}>Start de-identified case</button>
        </article>}
      </section>

      <section className="recent-cases">
        <div className="recent-cases-heading"><div><p className="micro-label">{syntheticOnly ? "Temporary evaluation history" : "Your organization"}</p><h2>Recent saved cases</h2></div><span>{cases.length} case{cases.length === 1 ? "" : "s"}</span></div>
        {loading ? <p className="case-list-empty">{syntheticOnly ? "Loading temporary evaluation history…" : "Loading private case history…"}</p> : cases.length ? (
          <div className="case-list">
            {cases.map((item) => (
              <button type="button" key={item.version_id} onClick={() => onOpenCase(item)}>
                <span className="case-list-avatar">{item.case_id.slice(0, 3).toUpperCase()}</span>
                <span><strong>{item.case_id}</strong><small>{item.change_summary}</small></span>
                <span><strong>Version {item.version_number}</strong><small>{new Date(item.created_at).toLocaleDateString()}</small></span>
                <b>Open →</b>
              </button>
            ))}
          </div>
        ) : <p className="case-list-empty">No cases have been saved in this workspace yet. Start with the synthetic case to learn the workflow.</p>}
      </section>

      <section className="privacy-boundary">
        <strong>{syntheticOnly ? "Synthetic-only boundary" : "Data boundary"}</strong>
        <p>{syntheticOnly ? "Do not enter or upload patient information. This evaluation accepts only the bundled synthetic teaching case, and saved demo history is temporary." : "Do not enter names, contact details, record numbers, exact dates, street addresses, or other direct identifiers. This software supports research decision workflows and does not replace clinician judgment."}</p>
      </section>
    </main>
  );
}
