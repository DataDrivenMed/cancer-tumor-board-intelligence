"use client";

import { useMemo, useRef, useState } from "react";

import {
  freshGuidedCase,
  freshGuidedFacts,
  guidedDocuments,
  guidedRawExtraction,
  type IntakeDocument,
  type ReviewFact,
} from "../data/synthetic-intake";
import { extractCaseDocument, type CaseExtractionResponse } from "../lib/tumor-board-api";

export type IntakeAuditEvent = {
  id: string;
  timestamp: string;
  action: string;
  detail: string;
};

export type ConfirmedIntake = {
  casePayload: Record<string, unknown>;
  rawExtraction: Record<string, unknown>;
  facts: ReviewFact[];
  documents: IntakeDocument[];
  events: IntakeAuditEvent[];
  extractionVersion: string;
};

type Props = {
  confirmed: boolean;
  initialIntake: ConfirmedIntake | null;
  initialMode?: "guided" | "upload";
  syntheticOnly?: boolean;
  onDirty: () => void;
  onConfirmed: (result: ConfirmedIntake) => void;
};

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function records(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value) ? value.map(record) : [];
}

function valueText(value: unknown): string {
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return "Not represented";
}

function provenanceFor(item: Record<string, unknown>): Record<string, unknown> {
  return records(item.provenance)[0] || {};
}

function sourceFact(
  id: string,
  label: string,
  item: Record<string, unknown>,
  value: unknown,
): ReviewFact {
  const provenance = provenanceFor(item);
  const segmentIds = Array.isArray(provenance.source_segment_ids)
    ? provenance.source_segment_ids.filter((entry): entry is string => typeof entry === "string")
    : [];
  return {
    id,
    label,
    value: valueText(value),
    status: valueText(item.status || "represented"),
    confidence: typeof item.confidence === "number" ? item.confidence : null,
    documentId: valueText(provenance.document_id || "DOC-001"),
    segmentId: segmentIds[0] || "S0001",
    excerpt: valueText(provenance.source_excerpt || "Source excerpt unavailable"),
    reviewState: "pending",
    correctionReason: "",
  };
}

function factsFromExtraction(response: CaseExtractionResponse): ReviewFact[] {
  const clinicalCase = response.case;
  const diagnosis = record(clinicalCase.diagnosis);
  const diseaseState = record(clinicalCase.disease_state);
  const performance = record(clinicalCase.performance_status);
  const pathology = records(clinicalCase.pathology)[0];
  const molecular = records(clinicalCase.molecular_findings)[0];
  const treatment = records(clinicalCase.treatments).at(-1);
  const lab = records(clinicalCase.labs)[0];
  return [
    sourceFact("diagnosis", "Diagnosis", diagnosis, diagnosis.value),
    sourceFact("disease_state", "Disease state", diseaseState, diseaseState.value),
    sourceFact("performance_status", "Performance status", performance, performance.value),
    pathology ? sourceFact("pathology", valueText(pathology.field || "Pathology"), pathology, pathology.value) : null,
    molecular ? sourceFact("molecular", "Molecular interpretation", molecular, molecular.laboratory_interpretation || `${valueText(molecular.gene)} ${valueText(molecular.alteration_type)}`) : null,
    treatment ? sourceFact("treatment", "Most recent treatment", treatment, treatment.regimen) : null,
    lab ? sourceFact("creatinine", valueText(lab.field || "Laboratory result"), lab, lab.value) : null,
  ].filter((item): item is ReviewFact => item !== null);
}

function applyReviewedFacts(
  sourceCase: Record<string, unknown>,
  facts: ReviewFact[],
  clinicalQuestionText: string,
): Record<string, unknown> {
  const next = structuredClone(sourceCase);
  const byId = Object.fromEntries(facts.map((fact) => [fact.id, fact]));
  const diagnosis = record(next.diagnosis);
  const diseaseState = record(next.disease_state);
  const performance = record(next.performance_status);
  diagnosis.value = byId.diagnosis?.value ?? diagnosis.value;
  diseaseState.value = byId.disease_state?.value ?? diseaseState.value;
  const numericPerformance = Number(byId.performance_status?.value);
  if (byId.performance_status && Number.isFinite(numericPerformance)) performance.value = numericPerformance;
  next.diagnosis = diagnosis;
  next.disease_state = diseaseState;
  next.performance_status = performance;

  const pathology = records(next.pathology);
  if (pathology[0] && byId.pathology) pathology[0].value = byId.pathology.value;
  next.pathology = pathology;
  const molecular = records(next.molecular_findings);
  if (molecular[0] && byId.molecular) molecular[0].laboratory_interpretation = byId.molecular.value;
  next.molecular_findings = molecular;
  const treatments = records(next.treatments);
  if (treatments.length && byId.treatment) treatments[treatments.length - 1].regimen = byId.treatment.value;
  next.treatments = treatments;
  const labs = records(next.labs);
  if (labs[0] && byId.creatinine) labs[0].value = byId.creatinine.value;
  next.labs = labs;

  const markVerified = (item: Record<string, unknown>) => {
    const provenance = records(item.provenance);
    item.human_verified = provenance.length > 0 && provenance.every((entry) => entry.source_verified === true);
  };
  [diagnosis, diseaseState, performance, ...pathology, ...labs].forEach(markVerified);
  molecular.forEach(markVerified);
  treatments.forEach(markVerified);
  const clinicalQuestion = record(next.clinical_question);
  clinicalQuestion.question = clinicalQuestionText.trim();
  next.clinical_question = clinicalQuestion;
  return next;
}

function toBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  const chunkSize = 0x8000;
  for (let index = 0; index < bytes.length; index += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(index, index + chunkSize));
  }
  return btoa(binary);
}

function event(action: string, detail: string): IntakeAuditEvent {
  return {
    id: `intake-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    timestamp: new Date().toISOString(),
    action,
    detail,
  };
}

export function CaseIntakeReview({ confirmed, initialIntake, initialMode = "guided", syntheticOnly = false, onDirty, onConfirmed }: Props) {
  const fileInput = useRef<HTMLInputElement>(null);
  const newUpload = !initialIntake && initialMode === "upload";
  const initialDocuments = initialIntake?.documents || (newUpload ? [] : guidedDocuments);
  const [mode, setMode] = useState<"guided" | "upload">(initialIntake ? (initialDocuments[0]?.documentId === "DOC-001" ? "upload" : "guided") : initialMode);
  const [documents, setDocuments] = useState<IntakeDocument[]>(initialDocuments);
  const [facts, setFacts] = useState<ReviewFact[]>(initialIntake?.facts.map((fact) => ({ ...fact })) || (newUpload ? [] : freshGuidedFacts()));
  const [baseCase, setBaseCase] = useState<Record<string, unknown>>(initialIntake?.casePayload || freshGuidedCase());
  const [rawExtraction, setRawExtraction] = useState<Record<string, unknown>>(initialIntake?.rawExtraction || (newUpload ? {} : guidedRawExtraction));
  const [extractionVersion, setExtractionVersion] = useState(initialIntake?.extractionVersion || (newUpload ? "Awaiting extraction" : "2.5.2 validated fixture"));
  const [events, setEvents] = useState<IntakeAuditEvent[]>(initialIntake?.events || (newUpload ? [] : [
    event("packet_loaded", "Validated synthetic AML source packet loaded for review."),
  ]));
  const [selectedDocumentId, setSelectedDocumentId] = useState(initialDocuments[0]?.documentId || "PATH-001");
  const [selectedSegmentId, setSelectedSegmentId] = useState(initialDocuments[0]?.segments[0]?.segmentId || "path-diagnosis");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");
  const [editReason, setEditReason] = useState("");
  const [attested, setAttested] = useState(confirmed);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [deidentificationAttested, setDeidentificationAttested] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [extractionError, setExtractionError] = useState("");
  const [extractionSummary, setExtractionSummary] = useState(initialIntake ? `${initialIntake.facts.length} clinician-reviewed facts restored from this local session` : newUpload ? "Choose an approved de-identified document to begin" : "7 source-linked facts ready for clinician review");
  const [clinicalQuestion, setClinicalQuestion] = useState(
    newUpload ? "" : valueText(record(initialIntake?.casePayload.clinical_question || freshGuidedCase().clinical_question).question),
  );

  const selectedDocument = documents.find((document) => document.documentId === selectedDocumentId) || documents[0];
  const reviewedCount = facts.filter((fact) => fact.reviewState !== "pending").length;
  const correctedCount = facts.filter((fact) => fact.reviewState === "corrected").length;
  const allReviewed = facts.length > 0 && reviewedCount === facts.length;
  const progress = facts.length ? Math.round((reviewedCount / facts.length) * 100) : 0;
  const provenanceCount = useMemo(
    () => facts.filter((fact) => Boolean(fact.documentId && fact.segmentId && fact.excerpt)).length,
    [facts],
  );

  const focusSource = (fact: ReviewFact) => {
    setSelectedDocumentId(fact.documentId);
    setSelectedSegmentId(fact.segmentId);
  };

  const updateFacts = (nextFacts: ReviewFact[], auditEvent?: IntakeAuditEvent) => {
    setFacts(nextFacts);
    setAttested(false);
    onDirty();
    if (auditEvent) setEvents((current) => [...current, auditEvent]);
  };

  const acceptFact = (fact: ReviewFact) => {
    updateFacts(
      facts.map((item) => item.id === fact.id ? { ...item, reviewState: "accepted", correctionReason: "" } : item),
      event("fact_accepted", `${fact.label} accepted with source ${fact.segmentId}.`),
    );
  };

  const acceptAll = () => {
    const pending = facts.filter((fact) => fact.reviewState === "pending").length;
    if (!pending) return;
    updateFacts(
      facts.map((fact) => fact.reviewState === "pending" ? { ...fact, reviewState: "accepted" } : fact),
      event("facts_bulk_accepted", `${pending} source-linked facts accepted after review.`),
    );
  };

  const startEditing = (fact: ReviewFact) => {
    focusSource(fact);
    setEditingId(fact.id);
    setEditValue(fact.value);
    setEditReason(fact.correctionReason);
  };

  const saveCorrection = (fact: ReviewFact) => {
    const value = editValue.trim();
    const reason = editReason.trim();
    if (!value || !reason) return;
    updateFacts(
      facts.map((item) => item.id === fact.id ? { ...item, value, correctionReason: reason, reviewState: "corrected" } : item),
      event("fact_corrected", `${fact.label} corrected with reason recorded; original source anchor retained.`),
    );
    setEditingId(null);
  };

  const loadGuidedPacket = () => {
    setMode("guided");
    setDocuments(guidedDocuments);
    setFacts(freshGuidedFacts());
    setBaseCase(freshGuidedCase());
    setRawExtraction(guidedRawExtraction);
    setExtractionVersion("2.5.2 validated fixture");
    setSelectedDocumentId("PATH-001");
    setSelectedSegmentId("path-diagnosis");
    setAttested(false);
    setDeidentificationAttested(false);
    setEditingId(null);
    setExtractionError("");
    setExtractionSummary("7 source-linked facts ready for clinician review");
    setClinicalQuestion(valueText(record(freshGuidedCase().clinical_question).question));
    const loaded = event("packet_loaded", "Validated synthetic AML source packet loaded for review.");
    setEvents([loaded]);
    onDirty();
  };

  const runExtraction = async () => {
    if (!selectedFile || !deidentificationAttested) return;
    if (selectedFile.size > 8 * 1024 * 1024) {
      setExtractionError("Choose a document smaller than 8 MB.");
      return;
    }
    setExtracting(true);
    setExtractionError("");
    try {
      const response = await extractCaseDocument({
        caseId: "TBI-INTAKE-001",
        caseType: "deidentified_research",
        documentId: "DOC-001",
        filename: selectedFile.name,
        contentBase64: toBase64(await selectedFile.arrayBuffer()),
        deidentificationAttested: true,
      });
      const nextDocuments: IntakeDocument[] = [{
        documentId: "DOC-001",
        filename: selectedFile.name,
        label: selectedFile.name,
        kind: selectedFile.name.split(".").at(-1)?.toUpperCase() || "DOC",
        segments: response.source_segments.map((segment) => ({
          segmentId: segment.segment_id,
          text: segment.text,
          page: segment.page,
          paragraph: segment.paragraph,
        })),
      }];
      const nextFacts = factsFromExtraction(response);
      setDocuments(nextDocuments);
      setFacts(nextFacts);
      setBaseCase(response.case);
      setRawExtraction(response.raw_extraction);
      setExtractionVersion(response.extraction_version);
      setSelectedDocumentId("DOC-001");
      setSelectedSegmentId(nextDocuments[0].segments[0]?.segmentId || "S0001");
      setAttested(false);
      setEditingId(null);
      setEvents([event("live_extraction_completed", `${selectedFile.name} processed into ${nextFacts.length} review facts.`)]);
      setExtractionSummary(`${response.deidentification_screen.status === "clear" ? "Identifier screen clear" : "Identifier screen blocked"}; ${response.provenance_verified}/${response.provenance_total} provenance anchors verified; original document retained: no`);
      setClinicalQuestion(valueText(record(response.case.clinical_question).question));
      onDirty();
    } catch (error) {
      setExtractionError(error instanceof Error ? error.message : "Live extraction could not complete.");
    } finally {
      setExtracting(false);
    }
  };

  const confirmRepresentation = () => {
    if (!allReviewed || !attested) return;
    const confirmation = event(
      "representation_confirmed",
      `${facts.length} facts confirmed; ${correctedCount} clinician corrections recorded.`,
    );
    const finalEvents = [...events, confirmation];
    setEvents(finalEvents);
    onConfirmed({
      casePayload: applyReviewedFacts(baseCase, facts, clinicalQuestion),
      rawExtraction,
      facts,
      documents,
      events: finalEvents,
      extractionVersion,
    });
  };

  return (
    <div className="intake-review-shell">
      <section className="intake-mode-card">
        <div className="intake-mode-copy">
          <p className="micro-label">Phase 4 source intake</p>
          <h3>Choose how to build the represented case</h3>
          <p>{syntheticOnly ? "This hosted evaluation uses only the controlled synthetic AML packet. Patient documents and de-identified clinical uploads are disabled." : "Source documents are processed transiently and are not retained. Only properly de-identified clinical information may be uploaded."}</p>
        </div>
        <div className="intake-mode-options" role="group" aria-label="Intake method">
          <button type="button" className={mode === "guided" ? "active" : ""} onClick={loadGuidedPacket}>
            <span>01</span><strong>Guided synthetic packet</strong><small>Always available for a safe demonstration</small>
          </button>
          {!syntheticOnly && <button type="button" className={mode === "upload" ? "active" : ""} onClick={() => setMode("upload")}>
            <span>02</span><strong>Local document extraction</strong><small>PDF, DOCX, TXT, or Markdown</small>
          </button>}
        </div>
        {!syntheticOnly && mode === "upload" && (
          <div className="upload-workbench">
            <input
              ref={fileInput}
              type="file"
              accept=".pdf,.docx,.txt,.md"
              onChange={(change) => {
                setSelectedFile(change.target.files?.[0] || null);
                setExtractionError("");
                setDeidentificationAttested(false);
              }}
            />
            <button type="button" className="upload-picker" onClick={() => fileInput.current?.click()}>
              <span>Choose a de-identified clinical document</span>
              <small>{selectedFile ? `${selectedFile.name} · ${(selectedFile.size / 1024).toFixed(0)} KB` : "Maximum 8 MB · processed transiently · not retained"}</small>
            </button>
            <label className="deidentification-attestation">
              <input type="checkbox" checked={deidentificationAttested} onChange={(change) => setDeidentificationAttested(change.target.checked)} />
              <span><strong>I confirm this document was de-identified before upload.</strong><small>The automated identifier screen is an added safeguard. It does not replace your organization&apos;s HIPAA de-identification process.</small></span>
            </label>
            <button type="button" className="primary-button" disabled={!selectedFile || !deidentificationAttested || extracting} onClick={() => void runExtraction()}>
              {extracting ? "Extracting source-linked facts…" : "Run live extraction"}
            </button>
            {extractionError && <div className="intake-error" role="alert"><strong>Extraction stopped safely</strong><span>{extractionError}</span><button type="button" onClick={loadGuidedPacket}>Use guided packet instead</button></div>}
          </div>
        )}
      </section>

      <section className="review-progress-card" aria-label="Intake review status">
        <div><span>Review progress</span><strong>{reviewedCount}/{facts.length} facts</strong></div>
        <div className="review-progress-track"><i style={{ width: `${progress}%` }} /></div>
        <div className="review-metrics">
          <span><strong>{provenanceCount}</strong> source linked</span>
          <span><strong>{correctedCount}</strong> corrected</span>
          <span><strong>{extractionVersion}</strong> extraction</span>
        </div>
        <p>{extractionSummary}</p>
      </section>

      <div className="source-review-grid">
        <section className="source-reader" aria-label="Source document viewer">
          <header>
            <div><p className="micro-label">Original source</p><h3>{selectedDocument?.label || "No source document"}</h3></div>
            <span className="source-only-badge">Source only</span>
          </header>
          <nav aria-label="Source documents">
            {documents.map((document) => (
              <button key={document.documentId} type="button" className={selectedDocumentId === document.documentId ? "active" : ""} onClick={() => setSelectedDocumentId(document.documentId)}>
                <span>{document.kind}</span>{document.label}
              </button>
            ))}
          </nav>
          <div className="source-segments">
            {selectedDocument?.segments.map((segment) => (
              <button
                key={segment.segmentId}
                type="button"
                className={selectedSegmentId === segment.segmentId ? "highlighted" : ""}
                onClick={() => setSelectedSegmentId(segment.segmentId)}
              >
                <span>{segment.segmentId}</span>
                <p>{segment.text}</p>
                <small>{segment.page ? `Page ${segment.page}` : ""}{segment.paragraph ? `${segment.page ? " · " : ""}Paragraph ${segment.paragraph}` : ""}</small>
              </button>
            ))}
          </div>
          <footer>Highlighted text is the exact source anchor for the selected proposed fact.</footer>
        </section>

        <section className="fact-review-panel" aria-label="Proposed fact review">
          <header>
            <div><p className="micro-label">Machine-proposed representation</p><h3>Review each decision-critical fact</h3></div>
            <button type="button" className="text-button" disabled={allReviewed} onClick={acceptAll}>Accept all source-linked</button>
          </header>
          <div className="review-fact-list">
            {facts.map((fact) => (
              <article className={`review-fact ${fact.reviewState}`} key={fact.id}>
                <div className="review-fact-heading">
                  <div><span>{fact.label}</span><strong>{fact.value}</strong></div>
                  <span className={`review-state ${fact.reviewState}`}>{fact.reviewState}</span>
                </div>
                <button type="button" className="source-anchor-button" onClick={() => focusSource(fact)}>
                  <span>{fact.documentId} · {fact.segmentId}</span>
                  <q>{fact.excerpt}</q>
                </button>
                <div className="review-fact-meta">
                  <span>Status: {fact.status.replaceAll("_", " ")}</span>
                  <span>{fact.confidence === null ? "Confidence not supplied" : `${Math.round(fact.confidence * 100)}% extraction confidence`}</span>
                </div>
                {editingId === fact.id ? (
                  <div className="correction-editor">
                    <label>Corrected represented value<input value={editValue} onChange={(change) => setEditValue(change.target.value)} /></label>
                    <label>Reason for correction<input value={editReason} onChange={(change) => setEditReason(change.target.value)} placeholder="Required for the audit record" /></label>
                    <div><button type="button" onClick={() => setEditingId(null)}>Cancel</button><button type="button" disabled={!editValue.trim() || !editReason.trim()} onClick={() => saveCorrection(fact)}>Save correction</button></div>
                  </div>
                ) : (
                  <div className="review-actions">
                    <button type="button" className="accept-button" onClick={() => acceptFact(fact)}>Accept fact</button>
                    <button type="button" onClick={() => startEditing(fact)}>Correct with reason</button>
                  </div>
                )}
              </article>
            ))}
          </div>
        </section>
      </div>

      <section className="question-framing-card">
        <div><p className="micro-label">Clinician-framed board question</p><h3>Define what the tumor board needs to discuss</h3><p>This question guides routing. It is authored or edited by the clinician and is not treated as an extracted patient fact.</p></div>
        <textarea
          aria-label="Tumor board question"
          value={clinicalQuestion}
          onChange={(change) => {
            setClinicalQuestion(change.target.value);
            onDirty();
          }}
        />
      </section>

      <section className={`representation-confirmation ${allReviewed ? "ready" : ""}`}>
        <div><p className="micro-label">Human decision boundary</p><h3>{confirmed ? "Representation confirmed" : allReviewed ? "Ready for clinician confirmation" : "Review all facts before confirmation"}</h3><p>Confirmation applies only to the source-linked case representation. It does not approve a diagnosis, treatment, or recommendation.</p></div>
        <label><input type="checkbox" checked={attested} disabled={!allReviewed} onChange={(change) => setAttested(change.target.checked)} /><span>I reviewed the represented facts against their displayed source anchors.</span></label>
        <button type="button" className="primary-button" disabled={!allReviewed || !attested} onClick={confirmRepresentation}>{confirmed ? "Confirm updated representation" : "Confirm representation and continue"}</button>
      </section>
    </div>
  );
}
