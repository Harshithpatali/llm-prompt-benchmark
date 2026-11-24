"""Prompt construction and response handling for the Universal Rubric Framework."""
from __future__ import annotations

import csv
import io
from pathlib import Path

from backend.rubric_qa import ATOMIC_CATEGORIES, HEADERS, OVERALL_ROWS, validate_csv

GUIDE_PATH = Path(__file__).resolve().parents[1] / "docs" / "RUBRIC_GENERATION_GUIDE.md"

def build_generation_prompt(scenario: str, guide: str | None = None) -> str:
    """Build a compact generation prompt that fits Groq's free-tier TPM budget.

    The full guide remains version-controlled as the canonical reference. Its
    output contract is represented here in a concise operational form; the
    deterministic validator and canonical O1-O14 rows enforce the hard rules.
    """
    if not scenario or not scenario.strip():
        raise ValueError("Scenario prompt cannot be empty")
    categories = sorted(ATOMIC_CATEGORIES)
    category_text = "\\n".join(f"- {category}" for category in categories)
    return f"""You design rigorous evaluation rubrics for assistant responses.

Create atomic, independently testable binary criteria from the scenario below.
Cover all materially relevant explicit requirements and important implicit
requirements, including safety, correctness, constraints, reasoning, context,
style, planning/actions when applicable, and output format. Do not add generic
criteria unrelated to the scenario. Split compound requirements into separate
criteria. Each criterion must be observable from the prompt and response.

Use only these nine parent categories:
{category_text}

Return ONLY CSV with exactly these nine columns, in this exact order:
"Rubric Component Number","Rubric Parent Category","Rubric Sub-Category","Rubric Component Name","Rubric Evaluation Question","Implicit vs. Explicit in the Prompt","Direct Quotation from the Prompt (N/A if Implicit)","Implicit Logic (N/A if Explicit)","Pass/Fail Criteria"

Rules:
- Atomic IDs are sequential C1, C2, ...; do not generate O rows.
- Every atomic row has exactly nine fields and every field is quoted.
- Parent category must be one of the nine categories listed above.
- Mark each requirement Explicit or Implicit.
- Explicit: quote the exact relevant words from the scenario; set Implicit Logic to N/A.
- Implicit: set quotation to N/A and explain the necessary inference in Implicit Logic.
- Evaluation question must test one requirement only.
- Pass/Fail Criteria must state a concrete, observable pass condition and what constitutes failure.
- Use N/A for non-applicable values; never leave fields empty.
- Escape embedded double quotes by doubling them. Do not include Markdown fences or prose.
- Aim for concise but comprehensive coverage; prioritize distinct requirements over repetition.

SCENARIO:
{scenario.strip()}
"""

def normalize_csv(raw: str) -> str:
    """Extract a nine-column CSV table and normalize harmless formatting.

    Models sometimes wrap CSV in prose/fences or omit CSV quoting. We only
    normalize when the header cells match the canonical schema exactly after
    trimming whitespace; we never guess or rename columns.
    """
    text = (raw or "").replace("\\ufeff", "").strip()
    if not text:
        return "\\n"
    lines = text.splitlines()
    # First try to locate a canonical CSV header, even if it is inside a fence
    # or preceded by a short explanation.
    start = None
    for i, line in enumerate(lines):
        candidate = line.strip()
        if candidate.startswith("```"):
            continue
        try:
            cells = next(csv.reader([candidate], strict=True))
        except (csv.Error, StopIteration):
            continue
        if [cell.strip() for cell in cells] == HEADERS:
            start = i
            break
    if start is not None:
        candidate_text = "\\n".join(lines[start:])
        try:
            rows = list(csv.reader(io.StringIO(candidate_text), strict=True))
        except csv.Error:
            rows = []
        if rows and [cell.strip() for cell in rows[0]] == HEADERS:
            output = io.StringIO()
            writer = csv.writer(output, quoting=csv.QUOTE_ALL, lineterminator="\\n")
            writer.writerow(HEADERS)
            for row in rows[1:]:
                if not row or all(not cell.strip() for cell in row):
                    continue
                writer.writerow([cell.strip() for cell in row])
            return output.getvalue()
    # Support Markdown pipe tables only when the header exactly matches.
    for i, line in enumerate(lines):
        candidate = line.strip().strip("|")
        cells = [cell.strip() for cell in candidate.split("|")]
        if cells == HEADERS:
            output = io.StringIO()
            writer = csv.writer(output, quoting=csv.QUOTE_ALL, lineterminator="\\n")
            writer.writerow(HEADERS)
            for data_line in lines[i + 1:]:
                data_line = data_line.strip()
                if not data_line or set(data_line.replace("|", "").replace(":", "").replace("-", "").strip()) == set():
                    continue
                if not data_line.startswith("|"):
                    break
                values = [cell.strip() for cell in data_line.strip("|").split("|")]
                if len(values) == 9:
                    writer.writerow(values)
            return output.getvalue()
    return text + "\\n"

def append_canonical_overall_rows(raw: str) -> str:
    """Replace any model-generated O rows with the immutable QA reference rows."""
    normalized = normalize_csv(raw)
    parsed = list(csv.reader(io.StringIO(normalized), strict=True))
    if not parsed or parsed[0] != HEADERS:
        return normalized
    atomic = [row for row in parsed[1:] if len(row) == 9 and not row[0].startswith("O")]
    canonical = [
        [number, "Overall Performance", subcategory, name, question, "N/A", "N/A", "N/A", "N/A"]
        for number, subcategory, name, question in OVERALL_ROWS
    ]
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL, lineterminator="\n")
    writer.writerow(HEADERS)
    writer.writerows(atomic + canonical)
    return output.getvalue()


def parse_and_validate(raw: str) -> tuple[str, dict]:
    normalized = append_canonical_overall_rows(raw)
    report = validate_csv(normalized)
    return normalized, report
