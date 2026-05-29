from __future__ import annotations

import pytest
from hypothesis import given

from chord_charts.model import Bar, CarryItem, ChordItem, ChordSymbol
from chord_charts.notes import pitch_class_for_lexeme
from chord_charts.validation import assert_valid_bar, validate_bar
from .strategies import valid_bars


def _chord_item(lexeme: str, start_beat: int, duration_beats: int) -> ChordItem:
    return ChordItem(
        chord=ChordSymbol(
            root_pc=pitch_class_for_lexeme(lexeme),
            suffix="",
            root_lexeme=lexeme,
        ),
        start_beat=start_beat,
        duration_beats=duration_beats,
    )


def test_validate_bar_accepts_single_chord_covering_bar() -> None:
    bar = Bar(beats=4, items=(_chord_item("C", 1, 4),))
    assert validate_bar(bar) == ()


def test_validate_bar_accepts_initial_carry_followed_by_chord() -> None:
    bar = Bar(
        beats=4,
        items=(
            CarryItem(start_beat=1, duration_beats=2),
            _chord_item("G", 3, 2),
        ),
    )
    assert validate_bar(bar) == ()


@pytest.mark.parametrize("beats", (0, -1))
def test_bar_rejects_non_positive_beats(beats: int) -> None:
    with pytest.raises(ValueError, match="bar beats must be positive"):
        Bar(beats=beats, items=())


@given(bar=valid_bars())
def test_validate_bar_accepts_generated_valid_bars(bar: Bar) -> None:
    assert validate_bar(bar) == ()
    assert_valid_bar(bar)


@pytest.mark.parametrize(
    ("bar", "expected_code"),
    (
        (Bar(beats=4, items=(_chord_item("C", 5, 1),)), "beat_range"),
        (
            Bar(
                beats=4,
                items=(
                    _chord_item("C", 1, 1),
                    _chord_item("G", 1, 3),
                ),
            ),
            "strictly_increasing_starts",
        ),
        (
            Bar(
                beats=4,
                items=(
                    _chord_item("C", 1, 3),
                    _chord_item("G", 3, 2),
                ),
            ),
            "non_overlap",
        ),
        (
            Bar(
                beats=4,
                items=(
                    _chord_item("C", 1, 2),
                    _chord_item("G", 4, 1),
                ),
            ),
            "full_bar_coverage",
        ),
        (
            Bar(
                beats=4,
                items=(
                    _chord_item("C", 1, 2),
                    CarryItem(start_beat=3, duration_beats=2),
                ),
            ),
            "carry_only_first",
        ),
        (
            Bar(beats=4, items=(_chord_item("C", 1, 0),)),
            "positive_duration",
        ),
    ),
)
def test_validate_bar_reports_requested_issue_codes(bar: Bar, expected_code: str) -> None:
    issue_codes = {issue.code for issue in validate_bar(bar)}
    assert expected_code in issue_codes


def test_validate_bar_reports_non_positive_duration_without_timeline_noise() -> None:
    bar = Bar(beats=4, items=(_chord_item("C", 1, 0),))

    issues = validate_bar(bar)

    assert {issue.code for issue in issues} == {"positive_duration"}


def test_validate_bar_reports_non_increasing_starts_without_overlap_noise() -> None:
    bar = Bar(
        beats=4,
        items=(
            _chord_item("C", 1, 3),
            _chord_item("G", 1, 1),
        ),
    )

    issues = validate_bar(bar)

    assert {issue.code for issue in issues} == {"strictly_increasing_starts"}


def test_assert_valid_bar_raises_value_error_for_invalid_bar() -> None:
    bar = Bar(
        beats=4,
        items=(
            _chord_item("C", 1, 2),
            CarryItem(start_beat=3, duration_beats=2),
        ),
    )

    with pytest.raises(ValueError, match="carry items may only appear first"):
        assert_valid_bar(bar)
