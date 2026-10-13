from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

from .io import iter_session_records
from .models import DialogState


@dataclass(frozen=True)
class ReportRow:
    block_name: str
    block_id: str
    context_name: str
    occurrences: int
    percentage: float


@dataclass(frozen=True)
class ReportSummary:
    total_sessions: int
    resolved_sessions: int
    unresolved_sessions: int
    output_path: Path


def build_rows(zip_path: Path, percentage_base: str) -> tuple[list[ReportRow], int, int]:
    counts: Counter[DialogState] = Counter()
    total_sessions = 0
    resolved_sessions = 0

    for session in iter_session_records(zip_path):
        total_sessions += 1
        if session.dialog_state is None:
            continue

        resolved_sessions += 1
        counts[session.dialog_state] += 1

    denominator = total_sessions if percentage_base == "all" else resolved_sessions
    rows: list[ReportRow] = []
    for dialog_state, occurrences in counts.items():
        percentage = (occurrences / denominator) if denominator else 0.0
        rows.append(
            ReportRow(
                block_name=dialog_state.block_name,
                block_id=dialog_state.block_id,
                context_name=dialog_state.context or "",
                occurrences=occurrences,
                percentage=percentage,
            )
        )

    rows.sort(key=lambda row: (-row.occurrences, row.block_name, row.block_id))
    return rows, total_sessions, resolved_sessions


def write_report(rows: list[ReportRow], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Last Block Report"
    sheet.freeze_panes = "A2"

    headers = [
        "Block name",
        "Block id",
        "Context name",
        "Occurrences as last block",
        "Overall percentage",
    ]
    sheet.append(headers)

    for cell in sheet[1]:
        cell.font = Font(bold=True)

    for row in rows:
        sheet.append([row.block_name, row.block_id, row.context_name, row.occurrences, row.percentage])

    sheet.auto_filter.ref = sheet.dimensions
    sheet.column_dimensions["A"].width = 40
    sheet.column_dimensions["B"].width = 40
    sheet.column_dimensions["C"].width = 32
    sheet.column_dimensions["D"].width = 24
    sheet.column_dimensions["E"].width = 18

    for cell in sheet["E"][1:]:
        cell.number_format = "0.00%"

    workbook.save(output_path)


def create_last_block_report(zip_path: Path, output_path: Path, percentage_base: str) -> ReportSummary:
    rows, total_sessions, resolved_sessions = build_rows(zip_path, percentage_base=percentage_base)
    write_report(rows, output_path)
    return ReportSummary(
        total_sessions=total_sessions,
        resolved_sessions=resolved_sessions,
        unresolved_sessions=total_sessions - resolved_sessions,
        output_path=output_path,
    )
