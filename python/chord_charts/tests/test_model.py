from __future__ import annotations

from collections.abc import Callable

import pytest

from chord_charts.model import (
    Bar,
    ChordSymbol,
    Meter,
    SectionBody,
    SectionEnding,
    TextRange,
)


@pytest.mark.parametrize(
    ("start_byte", "end_byte"),
    (
        (-1, 0),
        (2, 1),
    ),
)
def test_text_range_rejects_invalid_bounds(start_byte: int, end_byte: int) -> None:
    with pytest.raises(ValueError):
        TextRange(start_byte=start_byte, end_byte=end_byte)


@pytest.mark.parametrize(
    ("numerator", "denominator"),
    (
        (0, 4),
        (4, 8),
    ),
)
def test_meter_rejects_unsupported_values(numerator: int, denominator: int) -> None:
    with pytest.raises(ValueError):
        Meter(numerator=numerator, denominator=denominator)


def test_chord_symbol_rejects_mismatched_root_lexeme() -> None:
    with pytest.raises(ValueError, match="root_lexeme does not match root_pc"):
        ChordSymbol(root_pc=0, suffix="", root_lexeme="D")


@pytest.mark.parametrize("root_pc", (12, -1))
def test_chord_symbol_rejects_invalid_root_pitch_class(root_pc: int) -> None:
    with pytest.raises(ValueError, match="root_pc must be in 0..11"):
        ChordSymbol(root_pc=root_pc, suffix="", root_lexeme="C")


@pytest.mark.parametrize(
    ("bass_pc", "bass_lexeme"),
    (
        (7, None),
        (None, "G"),
    ),
)
def test_chord_symbol_requires_bass_fields_together(
    bass_pc: int | None, bass_lexeme: str | None
) -> None:
    with pytest.raises(
        ValueError,
        match="bass_pc and bass_lexeme must either both be set or both be None",
    ):
        ChordSymbol(
            root_pc=0,
            suffix="",
            root_lexeme="C",
            bass_pc=bass_pc,
            bass_lexeme=bass_lexeme,
        )


def test_chord_symbol_rejects_invalid_bass_pitch_class() -> None:
    with pytest.raises(ValueError, match="bass_pc must be in 0..11"):
        ChordSymbol(
            root_pc=0,
            suffix="",
            root_lexeme="C",
            bass_pc=12,
            bass_lexeme="G",
        )


def test_chord_symbol_rejects_mismatched_bass_lexeme() -> None:
    with pytest.raises(ValueError, match="bass_lexeme does not match bass_pc"):
        ChordSymbol(
            root_pc=0,
            suffix="",
            root_lexeme="C",
            bass_pc=7,
            bass_lexeme="A",
        )


def test_chord_symbol_accepts_matching_bass_fields() -> None:
    chord = ChordSymbol(
        root_pc=0,
        suffix="maj7",
        root_lexeme="C",
        bass_pc=7,
        bass_lexeme="G",
    )

    assert chord.bass_pc == 7
    assert chord.bass_lexeme == "G"


@pytest.mark.parametrize(
    "factory",
    (
        SectionBody,
        lambda rows: SectionEnding(name="1", rows=rows),
    ),
)
def test_section_rows_require_at_least_one_bar_per_row(
    factory: Callable[[tuple[tuple[Bar, ...], ...]], object],
) -> None:
    with pytest.raises(ValueError, match="section rows must contain at least one bar"):
        factory(((),))
