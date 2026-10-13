from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

from .io import iter_message_dialog_states
from .models import DialogState


@dataclass(frozen=True)
class FallbackCircularRow:
    block_name: str
    block_id: str
    context_name: str
    visits: int
    fallback_1: int
    fallback_2: int
    fallback_3_plus: int
    total_fallback_episodes: int


@dataclass(frozen=True)
class FallbackCircularSummary:
    total_sessions: int
    sessions_with_block_visits: int
    sessions_with_fallback_episodes: int
    output_path: Path


def _session_state_runs(zip_path: Path) -> tuple[dict[str, list[tuple[DialogState, int]]], int]:
    session_events: defaultdict[str, list[tuple[int, DialogState | None]]] = defaultdict(list)

    for internal_session_id, time_value, dialog_state in iter_message_dialog_states(zip_path):
        session_events[internal_session_id].append((time_value, dialog_state))

    collapsed_runs: dict[str, list[tuple[DialogState, int]]] = {}
    for internal_session_id, events in session_events.items():
        events.sort(key=lambda item: item[0])

        runs: list[tuple[DialogState, int]] = []
        current_state: DialogState | None = None
        run_length = 0

        for _, dialog_state in events:
            if dialog_state is None:
                continue

            if current_state == dialog_state:
                run_length += 1
                continue

            if current_state is not None:
                runs.append((current_state, run_length))

            current_state = dialog_state
            run_length = 1

        if current_state is not None:
            runs.append((current_state, run_length))

        collapsed_runs[internal_session_id] = runs

    return collapsed_runs, len(session_events)


def build_rows(zip_path: Path) -> tuple[list[FallbackCircularRow], int, int, int]:
    session_runs, total_sessions = _session_state_runs(zip_path)

    visits: Counter[DialogState] = Counter()
    fallback_1: Counter[DialogState] = Counter()
    fallback_2: Counter[DialogState] = Counter()
    fallback_3_plus: Counter[DialogState] = Counter()

    sessions_with_block_visits = 0
    sessions_with_fallback_episodes = 0

    for runs in session_runs.values():
        if not runs:
            continue

        sessions_with_block_visits += 1
        session_has_fallback = False

        for dialog_state, run_length in runs:
            visits[dialog_state] += 1

            fallbacks = run_length - 1
            if fallbacks <= 0:
                continue

            session_has_fallback = True
            if fallbacks == 1:
                fallback_1[dialog_state] += 1
            elif fallbacks == 2:
                fallback_2[dialog_state] += 1
            else:
                fallback_3_plus[dialog_state] += 1

        if session_has_fallback:
            sessions_with_fallback_episodes += 1

    all_blocks = set(visits)
    rows: list[FallbackCircularRow] = []
    for dialog_state in all_blocks:
        count_1 = fallback_1.get(dialog_state, 0)
        count_2 = fallback_2.get(dialog_state, 0)
        count_3_plus = fallback_3_plus.get(dialog_state, 0)
        rows.append(
            FallbackCircularRow(
                block_name=dialog_state.block_name,
                block_id=dialog_state.block_id,
                context_name=dialog_state.context or "",
                visits=visits[dialog_state],
                fallback_1=count_1,
                fallback_2=count_2,
                fallback_3_plus=count_3_plus,
                total_fallback_episodes=count_1 + count_2 + count_3_plus,
            )
        )

    rows.sort(
        key=lambda row: (
            -row.total_fallback_episodes,
            -row.fallback_3_plus,
            -row.fallback_2,
            -row.fallback_1,
            -row.visits,
            row.block_name,
            row.block_id,
        )
    )
    return rows, total_sessions, sessions_with_block_visits, sessions_with_fallback_episodes


def write_report(rows: list[FallbackCircularRow], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Fallback Circular"
    sheet.freeze_panes = "A2"

    headers = [
        "Block name",
        "Block id",
        "Context name",
        "Visits",
        "Fallbacks: 1",
        "Fallbacks: 2",
        "Fallbacks: 3+",
        "Total fallback episodes",
    ]
    sheet.append(headers)

    for cell in sheet[1]:
        cell.font = Font(bold=True)

    for row in rows:
        sheet.append(
            [
                row.block_name,
                row.block_id,
                row.context_name,
                row.visits,
                row.fallback_1,
                row.fallback_2,
                row.fallback_3_plus,
                row.total_fallback_episodes,
            ]
        )

    sheet.auto_filter.ref = sheet.dimensions
    sheet.column_dimensions["A"].width = 40
    sheet.column_dimensions["B"].width = 40
    sheet.column_dimensions["C"].width = 32
    sheet.column_dimensions["D"].width = 10
    sheet.column_dimensions["E"].width = 14
    sheet.column_dimensions["F"].width = 14
    sheet.column_dimensions["G"].width = 14
    sheet.column_dimensions["H"].width = 24

    workbook.save(output_path)


def create_fallback_circular_report(zip_path: Path, output_path: Path) -> FallbackCircularSummary:
    rows, total_sessions, sessions_with_block_visits, sessions_with_fallback_episodes = build_rows(zip_path)
    write_report(rows, output_path)
    return FallbackCircularSummary(
        total_sessions=total_sessions,
        sessions_with_block_visits=sessions_with_block_visits,
        sessions_with_fallback_episodes=sessions_with_fallback_episodes,
        output_path=output_path,
    )
