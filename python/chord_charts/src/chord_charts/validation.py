from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, final

from chord_charts.linearize import (
    _canonical_form,
    _form_reference_sequence,
    _render_ref,
    linearize_canonical_form,
)
from chord_charts.model import (
    Bar,
    BarItem,
    CarryItem,
    Document,
    Form,
    FormSectionRef,
    Section,
    TextRange,
)

BarValidationCode = Literal[
    "beat_range",
    "positive_duration",
    "strictly_increasing_starts",
    "non_overlap",
    "full_bar_coverage",
    "carry_only_first",
]

DocumentValidationCode = Literal[
    "unknown_section",
    "ending_required",
    "unexpected_ending",
    "unknown_ending",
    "form_sequence_mismatch",
    "unresolved_initial_carry",
]


@final
@dataclass(frozen=True, slots=True)
class BarValidationIssue:
    code: BarValidationCode
    message: str
    span: TextRange


@final
@dataclass(frozen=True, slots=True)
class DocumentValidationIssue:
    code: DocumentValidationCode
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


def validate_document(document: Document) -> tuple[DocumentValidationIssue, ...]:
    sections_by_name = {section.name: section for section in document.sections}
    canonical_form = _canonical_form(document)
    issues: list[DocumentValidationIssue] = []
    valid_sequences: list[tuple[Form, tuple[FormSectionRef, ...]]] = []
    canonical_sequence: tuple[FormSectionRef, ...] | None = None

    for form in document.forms:
        form_issues = _form_reference_issues(form=form, sections_by_name=sections_by_name)
        issues.extend(form_issues)
        if form_issues:
            continue

        reference_sequence = _form_reference_sequence(form)
        valid_sequences.append((form, reference_sequence))
        if form is canonical_form:
            canonical_sequence = reference_sequence

    if canonical_sequence is None:
        return tuple(issues)

    if _starts_with_unresolved_initial_carry(document):
        issues.append(
            _document_issue(
                code="unresolved_initial_carry",
                message="canonical form begins with a carry before any harmony has been established",
            )
        )

    for form, reference_sequence in valid_sequences:
        if reference_sequence != canonical_sequence:
            issues.append(
                _document_issue(
                    code="form_sequence_mismatch",
                    message=(
                        f"{_form_label(form)} must match the canonical reference sequence "
                        f"{_render_reference_sequence(canonical_sequence)}; got "
                        f"{_render_reference_sequence(reference_sequence)}"
                    ),
                )
            )

    return tuple(issues)


def assert_valid_bar(bar: Bar) -> None:
    issues = validate_bar(bar)
    if not issues:
        return

    joined_messages = "; ".join(issue.message for issue in issues)
    raise ValueError(joined_messages)


def assert_valid_document(document: Document) -> None:
    issues = validate_document(document)
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


def _starts_with_unresolved_initial_carry(document: Document) -> bool:
    linear_bars = linearize_canonical_form(document)
    if not linear_bars:
        return False

    first_bar = linear_bars[0].bar
    if not first_bar.items:
        return False

    return isinstance(first_bar.items[0], CarryItem)


def _form_reference_issues(
    *,
    form: Form,
    sections_by_name: dict[str, Section],
) -> tuple[DocumentValidationIssue, ...]:
    issues: list[DocumentValidationIssue] = []
    form_label = _form_label(form)

    for ref in _form_reference_sequence(form):
        section = sections_by_name.get(ref.name)
        rendered_ref = _render_ref(ref)

        if section is None:
            issues.append(
                _document_issue(
                    code="unknown_section",
                    message=f"{form_label} references unknown section {rendered_ref}",
                )
            )
            continue

        endings_by_name = {ending.name for ending in section.endings}
        if endings_by_name:
            if ref.ending is None:
                issues.append(
                    _document_issue(
                        code="ending_required",
                        message=(
                            f"{form_label} must reference section {ref.name!r} as "
                            f"[{ref.name}:ending] because the section has endings"
                        ),
                    )
                )
                continue

            if ref.ending not in endings_by_name:
                issues.append(
                    _document_issue(
                        code="unknown_ending",
                        message=f"{form_label} references unknown ending [{ref.name}:{ref.ending}]",
                    )
                )
            continue

        if ref.ending is not None:
            issues.append(
                _document_issue(
                    code="unexpected_ending",
                    message=(
                        f"{form_label} must reference section {ref.name!r} as "
                        f"[{ref.name}] because the section has no endings"
                    ),
                )
            )

    return tuple(issues)


def _issue(*, code: BarValidationCode, message: str, span: TextRange) -> BarValidationIssue:
    return BarValidationIssue(code=code, message=message, span=span)


def _document_issue(*, code: DocumentValidationCode, message: str) -> DocumentValidationIssue:
    return DocumentValidationIssue(code=code, message=message, span=TextRange.synthetic())


def _form_label(form: Form) -> str:
    if form.name is None:
        return "form:"
    return f"form[{form.name}]:"


def _render_reference_sequence(reference_sequence: tuple[FormSectionRef, ...]) -> str:
    if not reference_sequence:
        return "<empty>"
    return " ".join(_render_ref(ref) for ref in reference_sequence)
