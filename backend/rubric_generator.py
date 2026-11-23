"""Prompt construction and response handling for the Universal Rubric Framework."""
from __future__ import annotations

import csv
import io
from pathlib import Path

from backend.rubric_qa import HEADERS, OVERALL_ROWS, validate_csv

GUIDE_PATH = Path(__file__).resolve().parents[1] / "docs" / "RUBRIC_GENERATION_GUIDE.md"

def build_generation_prompt(scenario: str, guide: str | None = None) -> str:
    if not scenario or not scenario.strip():
        raise ValueError("Scenario prompt cannot be empty")
    source = guide if guide is not None else GUIDE_PATH.read_text(encoding="utf-8")
    return f"""You are an expert LLM evaluation-rubric designer. Follow the supplied Universal Rubric Generation Guide as the source of truth. Do not invent prompt quotations. Every atomic row must test one independently observable requirement. Include relevant explicit and implicit requirements, and append the exact 14 Overall Performance rows specified in the guide's companion QA specification. Return ONLY raw CSV: no Markdown fences or commentary. Quote every field, escape embedded quotes by doubling them, include exactly these nine columns: {','.join(HEADERS)}. Use C1..Cn for atomic rows and O1..O14 for holistic rows. Do not claim unsupported ground truth.

UNIVERSAL RUBRIC GENERATION GUIDE:
{source}

SCENARIO PROMPT TO EVALUATE:
{scenario}
"""

def normalize_csv(raw: str) -> str:
    text = (raw or "").strip()
    if text.startswith("\`\`\`"):
        lines = text.splitlines()
        if lines and lines[0].startswith("\`\`\`"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "\`\`\`":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    # Strip accidental prose only when a valid header line can be located.
    lines = text.splitlines()
    header = ",".join(f'"{h}"' for h in HEADERS)
    start = next((i for i,line in enumerate(lines) if line.strip()==header), None)
    if start is not None:
        text = "\n".join(lines[start:])
    return text + "\n"

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
