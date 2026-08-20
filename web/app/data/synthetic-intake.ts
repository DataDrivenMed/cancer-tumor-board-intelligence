import { syntheticCase } from "./synthetic-case";

export type SourceSegment = {
  segmentId: string;
  text: string;
  page?: number | null;
  paragraph?: number | null;
};

export type IntakeDocument = {
  documentId: string;
  filename: string;
  label: string;
  kind: string;
  segments: SourceSegment[];
};

export type ReviewFact = {
  id: string;
  label: string;
  value: string;
  status: string;
  confidence: number | null;
  documentId: string;
  segmentId: string;
  excerpt: string;
  reviewState: "pending" | "accepted" | "corrected";
  correctionReason: string;
};

export const guidedDocuments: IntakeDocument[] = [
  {
    documentId: "PATH-001",
    filename: "synthetic-bone-marrow-pathology.txt",
    label: "Bone marrow pathology",
    kind: "PATH",
    segments: [
      { segmentId: "path-diagnosis", paragraph: 1, text: "Synthetic marrow report represents acute myeloid leukemia." },
      { segmentId: "path-blasts", paragraph: 2, text: "Marrow contains 34% myeloblasts in this synthetic record." },
    ],
  },
  {
    documentId: "NOTE-001",
    filename: "synthetic-hematology-consultation.txt",
    label: "Hematology consultation",
    kind: "NOTE",
    segments: [
      { segmentId: "note-state", paragraph: 1, text: "Synthetic consultation represents first relapse after prior therapy." },
      { segmentId: "note-ecog", paragraph: 2, text: "ECOG performance status 1 is explicitly represented." },
      { segmentId: "note-treatment", paragraph: 3, text: "Prior induction and complete remission are represented." },
      { segmentId: "note-creatinine", paragraph: 4, text: "Creatinine 0.9 mg/dL." },
    ],
  },
  {
    documentId: "LAB-001",
    filename: "synthetic-molecular-panel.txt",
    label: "Molecular panel",
    kind: "LAB",
    segments: [
      { segmentId: "lab-flt3", paragraph: 1, text: "FLT3-ITD is explicitly represented in the synthetic panel." },
    ],
  },
];

export const guidedReviewFacts: ReviewFact[] = [
  { id: "diagnosis", label: "Diagnosis", value: "acute myeloid leukemia", status: "confirmed", confidence: 1, documentId: "PATH-001", segmentId: "path-diagnosis", excerpt: "Synthetic marrow report represents acute myeloid leukemia.", reviewState: "pending", correctionReason: "" },
  { id: "disease_state", label: "Disease state", value: "first relapse", status: "confirmed", confidence: 1, documentId: "NOTE-001", segmentId: "note-state", excerpt: "Synthetic consultation represents first relapse after prior therapy.", reviewState: "pending", correctionReason: "" },
  { id: "performance_status", label: "Performance status", value: "1", status: "confirmed", confidence: 1, documentId: "NOTE-001", segmentId: "note-ecog", excerpt: "ECOG performance status 1 is explicitly represented.", reviewState: "pending", correctionReason: "" },
  { id: "pathology", label: "Bone marrow blasts", value: "34% myeloblasts", status: "confirmed", confidence: 1, documentId: "PATH-001", segmentId: "path-blasts", excerpt: "Marrow contains 34% myeloblasts in this synthetic record.", reviewState: "pending", correctionReason: "" },
  { id: "molecular", label: "Molecular interpretation", value: "FLT3-ITD detected", status: "confirmed", confidence: 1, documentId: "LAB-001", segmentId: "lab-flt3", excerpt: "FLT3-ITD is explicitly represented in the synthetic panel.", reviewState: "pending", correctionReason: "" },
  { id: "treatment", label: "Prior treatment", value: "cytarabine plus anthracycline induction", status: "confirmed", confidence: 1, documentId: "NOTE-001", segmentId: "note-treatment", excerpt: "Prior induction and complete remission are represented.", reviewState: "pending", correctionReason: "" },
  { id: "creatinine", label: "Creatinine", value: "0.9 mg/dL", status: "confirmed", confidence: 1, documentId: "NOTE-001", segmentId: "note-creatinine", excerpt: "Creatinine 0.9 mg/dL.", reviewState: "pending", correctionReason: "" },
];

export const guidedRawExtraction: Record<string, unknown> = {
  fixture: "phase4-guided-synthetic-intake",
  extraction_version: "2.5.2-fixture",
  diagnosis: { value: "acute myeloid leukemia", status: "confirmed", source_segment_ids: ["path-diagnosis"] },
  disease_state: { value: "first relapse", status: "confirmed", source_segment_ids: ["note-state"] },
  performance_status: { value: "1", status: "confirmed", source_segment_ids: ["note-ecog"] },
  extraction_warnings: [],
};

export function freshGuidedCase(): Record<string, unknown> {
  return structuredClone(syntheticCase);
}

export function freshGuidedFacts(): ReviewFact[] {
  return guidedReviewFacts.map((fact) => ({ ...fact }));
}
