from __future__ import annotations

from typing import cast

import pytest
from hypothesis import given

from chord_charts.notes import (
    ACCEPTED_INPUT_LEXEMES,
    NoteSpellingPolicy,
    pitch_class_for_lexeme,
    render_pitch_class,
    respell_note_lexeme,
)
from . import strategies

EXPECTED_PITCH_CLASSES = {
    "C": 0,
    "K": 1,
    "C#": 1,
    "Db": 1,
    "D": 2,
    "L": 3,
    "D#": 3,
    "Eb": 3,
    "E": 4,
    "F": 5,
    "H": 6,
    "F#": 6,
    "Gb": 6,
    "G": 7,
    "I": 8,
    "G#": 8,
    "Ab": 8,
    "A": 9,
    "J": 10,
    "A#": 10,
    "Bb": 10,
    "B": 11,
}

EXPECTED_RENDER_TABLES: dict[NoteSpellingPolicy, tuple[str, ...]] = {
    "hij": ("C", "K", "D", "L", "E", "F", "H", "G", "I", "A", "J", "B"),
    "accidental(flat-heavy)": (
        "C",
        "Db",
        "D",
        "Eb",
        "E",
        "F",
        "F#",
        "G",
        "Ab",
        "A",
        "Bb",
        "B",
    ),
    "accidental(sharp-heavy)": (
        "C",
        "C#",
        "D",
        "D#",
        "E",
        "F",
        "F#",
        "G",
        "G#",
        "A",
        "Bb",
        "B",
    ),
}


@pytest.mark.parametrize(("lexeme", "expected_pitch_class"), EXPECTED_PITCH_CLASSES.items())
def test_pitch_class_for_accepted_input_lexemes(lexeme: str, expected_pitch_class: int) -> None:
    assert pitch_class_for_lexeme(lexeme) == expected_pitch_class


def test_accepted_input_lexemes_are_fully_covered() -> None:
    assert set(EXPECTED_PITCH_CLASSES) == set(ACCEPTED_INPUT_LEXEMES)


@pytest.mark.parametrize(("policy", "expected_table"), EXPECTED_RENDER_TABLES.items())
def test_render_pitch_class_uses_expected_spelling_tables(
    policy: NoteSpellingPolicy, expected_table: tuple[str, ...]
) -> None:
    actual_table = tuple(render_pitch_class(pitch_class, policy) for pitch_class in range(12))
    assert actual_table == expected_table


def test_sharp_heavy_keeps_bb_instead_of_a_sharp() -> None:
    assert render_pitch_class(10, "accidental(sharp-heavy)") == "Bb"


@pytest.mark.parametrize("pitch_class", (12, -1))
def test_render_pitch_class_rejects_invalid_pitch_class(pitch_class: int) -> None:
    with pytest.raises(ValueError, match="pitch class must be in 0..11"):
        render_pitch_class(pitch_class, "hij")


def test_invalid_note_lexeme_raises_value_error() -> None:
    with pytest.raises(ValueError, match="unsupported note lexeme"):
        pitch_class_for_lexeme("Cb")


def test_invalid_note_spelling_policy_raises_value_error() -> None:
    with pytest.raises(ValueError, match="unsupported note spelling policy"):
        render_pitch_class(0, cast(NoteSpellingPolicy, "bad-policy"))


@given(lexeme=strategies.accepted_note_lexemes(), policy=strategies.note_spelling_policies())
def test_respelling_preserves_pitch_class(
    lexeme: str, policy: NoteSpellingPolicy
) -> None:
    respelled = respell_note_lexeme(lexeme, policy)
    assert pitch_class_for_lexeme(respelled) == pitch_class_for_lexeme(lexeme)


@given(pitch_class=strategies.pitch_classes(), policy=strategies.note_spelling_policies())
def test_rendered_pitch_classes_round_trip_and_are_idempotent(
    pitch_class: int, policy: NoteSpellingPolicy
) -> None:
    rendered = render_pitch_class(pitch_class, policy)
    assert rendered in ACCEPTED_INPUT_LEXEMES
    assert pitch_class_for_lexeme(rendered) == pitch_class
    assert render_pitch_class(pitch_class_for_lexeme(rendered), policy) == rendered
