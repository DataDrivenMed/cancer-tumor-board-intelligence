from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class IdentifierPattern:
    category: str
    expression: re.Pattern[str]
    explanation: str


PATTERNS = (
    IdentifierPattern("email", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I), "Email addresses are direct identifiers."),
    IdentifierPattern("telephone", re.compile(r"(?<!\d)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?!\d)"), "Telephone and fax numbers are direct identifiers."),
    IdentifierPattern("social_security_number", re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "Social Security numbers are direct identifiers."),
    IdentifierPattern("medical_record_number", re.compile(r"\b(?:MRN|medical record(?: number)?)[\s:#-]*[A-Z0-9-]{4,}\b", re.I), "Medical record numbers must be removed."),
    IdentifierPattern("account_or_beneficiary_number", re.compile(r"\b(?:account|member|beneficiary|policy)[\s:#-]*(?:number|no\.?|id)?[\s:#-]*[A-Z0-9-]{4,}\b", re.I), "Account and beneficiary numbers must be removed."),
    IdentifierPattern("patient_name", re.compile(r"\b(?:patient|name)[\s:]+[A-Z][A-Za-z'’-]+(?:\s+[A-Z][A-Za-z'’-]+){1,3}\b"), "Patient and family names must be removed."),
    IdentifierPattern("street_address", re.compile(r"\b\d{1,6}\s+[A-Za-z0-9.'’-]+(?:\s+[A-Za-z0-9.'’-]+){0,4}\s+(?:Street|St|Road|Rd|Avenue|Ave|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct)\b", re.I), "Street addresses must be removed."),
    IdentifierPattern("full_date", re.compile(r"\b(?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b"), "Month and day elements of patient-related dates are identifiers under Safe Harbor."),
    IdentifierPattern("written_date", re.compile(r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(?:[12]?\d|3[01])(?:st|nd|rd|th)?,?\s+(?:19|20)\d{2}\b", re.I), "Written month and day elements must be removed."),
    IdentifierPattern("network_identifier", re.compile(r"\b(?:https?://\S+|(?:\d{1,3}\.){3}\d{1,3})\b", re.I), "URLs and IP addresses are direct identifiers."),
    IdentifierPattern("age_over_89", re.compile(r"\b(?:age[d]?\s*[:=]?\s*|)(?:9\d|1[01]\d|120)(?:[- ]year[- ]old|\s*years?\s*old)\b", re.I), "Ages above 89 must be grouped as age 90 or older under Safe Harbor."),
)


def _masked_excerpt(text: str, start: int, end: int) -> str:
    left = max(0, start - 28)
    right = min(len(text), end + 28)
    value = text[left:right]
    for identifier_pattern in PATTERNS:
        value = identifier_pattern.expression.sub("[identifier removed]", value)
    return " ".join(value.split())[:180]


def screen_deidentified_text(texts: Iterable[str]) -> dict:
    findings: list[dict[str, str | int]] = []
    for source_index, text in enumerate(texts, start=1):
        for pattern in PATTERNS:
            for match in pattern.expression.finditer(text):
                findings.append(
                    {
                        "category": pattern.category,
                        "source_index": source_index,
                        "start": match.start(),
                        "end": match.end(),
                        "masked_context": _masked_excerpt(text, match.start(), match.end()),
                        "explanation": pattern.explanation,
                    }
                )
    return {
        "status": "blocked" if findings else "clear",
        "finding_count": len(findings),
        "findings": findings[:50],
        "scanner_version": "1.0.0",
        "original_document_retained": False,
        "boundary": (
            "This automated screen is a secondary safeguard, not a Safe Harbor or Expert Determination certification. "
            "Users must de-identify source material before upload."
        ),
    }
