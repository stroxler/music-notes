from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, final

from chord_charts.model import Bar, BarItem, CarryItem, TextRange

BarValidationCode = Literal[
    "beat_range",
    "positive_duration",
    "strictly_increasing_starts",
    "non_overlap",
    "full_bar_coverage",
    "carry_only_first",
]


@final
@dataclass(frozen=True, slots=True)
class BarValidationIssue:
    code: BarValidationCode
    message: str
    span: TextRange


def validate_bar(bar: Bar) -> tuple[BarValidationIssue, ...]:
    if not bar.items:
        return (
            _issue(
                code="full_bar_coverage",
                message="bar must contain at least one item",
                span=bar.span,
            ),
        )

    issues: list[BarValidationIssue] = []

    previous_start: int | None = None
    previous_end: int | None = None
    can_check_timeline = True

    for index, item in enumerate(bar.items):
        blocks_timeline = False

        if item.start_beat < 1 or item.start_beat > bar.beats:
            issues.append(
                _issue(
                    code="beat_range",
                    message=(
                        f"item {index} starts at beat {item.start_beat}, "
                        f"outside 1..{bar.beats}"
                    ),
                    span=item.span,
                )
            )
            blocks_timeline = True

        if item.duration_beats < 1:
            issues.append(
                _issue(
                    code="positive_duration",
                    message=(
                        f"item {index} has non-positive duration "
                        f"{item.duration_beats}"
                    ),
                    span=item.span,
                )
            )
            blocks_timeline = True

        if index != 0 and isinstance(item, CarryItem):
            issues.append(
                _issue(
                    code="carry_only_first",
                    message=f"item {index} is a carry; carry items may only appear first",
                    span=item.span,
                )
            )

        if previous_start is not None and item.start_beat <= previous_start:
            issues.append(
                _issue(
                    code="strictly_increasing_starts",
                    message=(
                        f"item {index} starts at beat {item.start_beat}, "
                        f"which is not after beat {previous_start}"
                    ),
                    span=item.span,
                )
            )
            blocks_timeline = True

        if blocks_timeline:
            can_check_timeline = False

        if can_check_timeline:
            issues.extend(
                _timeline_issues(
                    bar=bar,
                    index=index,
                    item=item,
                    previous_end=previous_end,
                )
            )

        previous_start = item.start_beat
        previous_end = _item_end(item)

    if can_check_timeline and previous_end != bar.beats + 1:
        issues.append(
            _issue(
                code="full_bar_coverage",
                message=(
                    f"bar must end at beat {bar.beats + 1}, "
                    f"but the last item ends at beat {previous_end}"
                ),
                span=bar.span,
            )
        )

    return tuple(issues)


def assert_valid_bar(bar: Bar) -> None:
    issues = validate_bar(bar)
    if not issues:
        return

    joined_messages = "; ".join(issue.message for issue in issues)
    raise ValueError(joined_messages)


def _item_end(item: BarItem) -> int:
    return item.start_beat + item.duration_beats


def _timeline_issues(
    *, bar: Bar, index: int, item: BarItem, previous_end: int | None
) -> tuple[BarValidationIssue, ...]:
    if previous_end is None:
        if item.start_beat == 1:
            return ()
        return (
            _issue(
                code="full_bar_coverage",
                message=f"bar must start at beat 1, got beat {item.start_beat}",
                span=item.span,
            ),
        )

    if item.start_beat < previous_end:
        return (
            _issue(
                code="non_overlap",
                message=(
                    f"item {index} starts at beat {item.start_beat}, "
                    f"before the previous item ends at beat {previous_end}"
                ),
                span=item.span,
            ),
        )

    if item.start_beat > previous_end:
        return (
            _issue(
                code="full_bar_coverage",
                message=(
                    f"bar has a gap before item {index}: "
                    f"expected beat {previous_end}, got beat {item.start_beat}"
                ),
                span=item.span,
            ),
        )

    return ()


def _issue(*, code: BarValidationCode, message: str, span: TextRange) -> BarValidationIssue:
    return BarValidationIssue(code=code, message=message, span=span)
