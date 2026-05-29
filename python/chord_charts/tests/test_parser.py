from __future__ import annotations

from collections.abc import Callable

import pytest
import chord_charts
from hypothesis import given
from hypothesis import strategies as st

from chord_charts.model import Bar, CarryItem, ChordItem, ChordSymbol
from chord_charts.notes import pitch_class_for_lexeme
from chord_charts.parser import (
    FormHeader,
    ParsedFormBlock,
    ParsedSectionBlock,
    SectionHeader,
    parse_canonical_bar_cell,
    parse_canonical_section_row,
    parse_chord_token,
    parse_form_header,
    parse_section_header,
    parse_source_blocks,
)
from . import strategies

_SUFFIX_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#+()-"
_ROOT_EXTENSION_PREFIXES = {
    "A": "#b",
    "B": "b",
    "C": "#",
    "D": "#b",
    "F": "#",
    "G": "#b",
}
_SUFFIX_TEXT = st.text(alphabet=_SUFFIX_ALPHABET, min_size=0, max_size=8)


def _chord_item(
    lexeme: str,
    start_beat: int,
    duration_beats: int,
    *,
    suffix: str = "",
    bass_lexeme: str | None = None,
) -> ChordItem:
    return ChordItem(
        chord=ChordSymbol(
            root_pc=pitch_class_for_lexeme(lexeme),
            suffix=suffix,
            root_lexeme=lexeme,
            bass_pc=None if bass_lexeme is None else pitch_class_for_lexeme(bass_lexeme),
            bass_lexeme=bass_lexeme,
        ),
        start_beat=start_beat,
        duration_beats=duration_beats,
    )


def _chord_text(chord: ChordSymbol) -> str:
    if chord.bass_lexeme is None:
        return f"{chord.root_lexeme}{chord.suffix}"
    return f"{chord.root_lexeme}{chord.suffix}/{chord.bass_lexeme}"


def _assert_chord_symbol(
    chord: ChordSymbol,
    *,
    root_lexeme: str,
    suffix: str = "",
    bass_lexeme: str | None = None,
) -> None:
    assert chord.root_lexeme == root_lexeme
    assert chord.root_pc == pitch_class_for_lexeme(root_lexeme)
    assert chord.suffix == suffix
    assert chord.bass_lexeme == bass_lexeme
    assert chord.bass_pc == (
        None if bass_lexeme is None else pitch_class_for_lexeme(bass_lexeme)
    )


def _render_canonical_bar_cell(bar: Bar) -> str:
    token_texts = [
        "-" if isinstance(item, CarryItem) else _chord_text(item.chord) for item in bar.items
    ]
    slot_width = 1

    for index, item in enumerate(bar.items):
        token = token_texts[index]
        if index + 1 < len(bar.items):
            beats_until_next = bar.items[index + 1].start_beat - item.start_beat
            slot_width = max(slot_width, (len(token) + beats_until_next) // beats_until_next)
        else:
            beats_to_bar_end = bar.beats - item.start_beat + 1
            slot_width = max(
                slot_width, (len(token) + beats_to_bar_end - 1) // beats_to_bar_end
            )

    cell = [" "] * (bar.beats * slot_width)
    for item, token in zip(bar.items, token_texts, strict=True):
        start_column = (item.start_beat - 1) * slot_width
        cell[start_column : start_column + len(token)] = list(token)

    return "".join(cell)


def _render_canonical_section_row(bars: tuple[Bar, ...], *, leading_indent: str = "") -> str:
    cells = "".join(f"|{_render_canonical_bar_cell(bar)}" for bar in bars)
    return f"{leading_indent}{cells}|"


@st.composite
def _canonical_bars(draw: st.DrawFn, *, min_beats: int = 1, max_beats: int = 8) -> Bar:
    beats = draw(st.integers(min_value=min_beats, max_value=max_beats))
    item_count = draw(st.integers(min_value=1, max_value=beats))

    split_points: list[int]
    if item_count == 1:
        split_points = []
    else:
        split_points = sorted(
            draw(
                st.lists(
                    st.integers(min_value=2, max_value=beats),
                    min_size=item_count - 1,
                    max_size=item_count - 1,
                    unique=True,
                )
            )
        )

    starts = [1, *split_points]
    ends = [*starts[1:], beats + 1]
    first_item_is_carry = draw(st.booleans())

    items: list[CarryItem | ChordItem] = []
    for index, (start, end) in enumerate(zip(starts, ends, strict=True)):
        duration = end - start

        if index == 0 and first_item_is_carry:
            items.append(CarryItem(start_beat=start, duration_beats=duration))
            continue

        root_lexeme, suffix, bass_lexeme = draw(_chord_token_cases())
        items.append(
            _chord_item(
                root_lexeme,
                start,
                duration,
                suffix=suffix,
                bass_lexeme=bass_lexeme,
            )
        )

    return Bar(beats=beats, items=tuple(items))


@st.composite
def _chord_token_cases(
    draw: st.DrawFn,
) -> tuple[str, str, str | None]:
    root_lexeme = draw(strategies.accepted_note_lexemes())
    suffix_strategy = _SUFFIX_TEXT
    leading_extensions = _ROOT_EXTENSION_PREFIXES.get(root_lexeme)
    if leading_extensions is not None:
        suffix_strategy = suffix_strategy.filter(
            lambda value: not value or value[0] not in leading_extensions
        )
    suffix = draw(suffix_strategy)
    bass_lexeme = draw(st.one_of(st.none(), strategies.accepted_note_lexemes()))
    return root_lexeme, suffix, bass_lexeme


@st.composite
def _canonical_section_row_cases(
    draw: st.DrawFn,
) -> tuple[int, tuple[Bar, ...], str]:
    beats = draw(st.integers(min_value=1, max_value=8))
    bars = tuple(
        draw(
            st.lists(
                _canonical_bars(min_beats=beats, max_beats=beats),
                min_size=1,
                max_size=4,
            )
        )
    )
    leading_indent = draw(st.sampled_from(("", " ", "    ", "\t")))
    return beats, bars, leading_indent


@pytest.mark.parametrize(
    ("text", "expected"),
    (
        ("[A]:", SectionHeader(name="A")),
        ("[A:1]:", SectionHeader(name="A", ending="1")),
        ("[bridge-out]:", SectionHeader(name="bridge-out")),
    ),
)
def test_parse_section_header_examples(text: str, expected: SectionHeader) -> None:
    assert parse_section_header(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    (
        ("form:", FormHeader()),
        ("form[lyrics]:", FormHeader(name="lyrics")),
        ("form[set-1]:", FormHeader(name="set-1")),
    ),
)
def test_parse_form_header_examples(text: str, expected: FormHeader) -> None:
    assert parse_form_header(text) == expected


@pytest.mark.parametrize(
    ("parser", "text"),
    (
        (parse_section_header, "[A]"),
        (parse_section_header, "[A :1]:"),
        (parse_section_header, "[A:]:"),
        (parse_form_header, "form"),
        (parse_form_header, "form[]:"),
        (parse_form_header, "form[lyrics]"),
    ),
)
def test_block_header_parsers_reject_invalid_input(
    parser: Callable[[str], object],
    text: str,
) -> None:
    with pytest.raises(ValueError):
        parser(text)


def test_parse_source_blocks_splits_sections_and_forms() -> None:
    text = "\n".join(
        (
            "[A]:",
            "    |C   |F   |",
            "",
            "[A:1]:",
            "    |G7  |C   |",
            "form:",
            "[A:1]",
            "form[lyrics]:",
            "[A:1]",
            "",
            "just friends",
        )
    )

    assert parse_source_blocks(text, beats=4) == (
        ParsedSectionBlock(
            header=SectionHeader(name="A"),
            rows=((Bar(beats=4, items=(_chord_item("C", 1, 4),)), Bar(beats=4, items=(_chord_item("F", 1, 4),))),),
        ),
        ParsedSectionBlock(
            header=SectionHeader(name="A", ending="1"),
            rows=(
                (
                    Bar(beats=4, items=(_chord_item("G", 1, 4, suffix="7"),)),
                    Bar(beats=4, items=(_chord_item("C", 1, 4),)),
                ),
            ),
        ),
        ParsedFormBlock(
            header=FormHeader(),
            body_lines=("[A:1]",),
        ),
        ParsedFormBlock(
            header=FormHeader(name="lyrics"),
            body_lines=("[A:1]", "", "just friends"),
        ),
    )


def test_parse_source_blocks_rejects_content_before_first_block() -> None:
    with pytest.raises(ValueError, match="before first section or form header"):
        parse_source_blocks("title: Just Friends\n[A]:\n| C   |", beats=4)


def test_parse_source_blocks_rejects_form_before_any_section_block() -> None:
    with pytest.raises(ValueError, match="form blocks must follow at least one section block"):
        parse_source_blocks("form:\n[A:1]", beats=4)


def test_parse_source_blocks_rejects_section_after_form_block() -> None:
    text = "\n".join(
        (
            "[A]:",
            "|C   |",
            "form:",
            "[A]",
            "[B]:",
            "|F   |",
        )
    )

    with pytest.raises(ValueError, match="section blocks must not appear after form blocks"):
        parse_source_blocks(text, beats=4)


def test_parse_source_blocks_rejects_empty_section_block() -> None:
    with pytest.raises(ValueError, match="section block 'A' must contain at least one row"):
        parse_source_blocks("[A]:\n\nform:\n[A]", beats=4)


def test_parse_canonical_section_row_trims_leading_indentation() -> None:
    row = parse_canonical_section_row("    |C   |G7  |", beats=4)

    assert row == (
        Bar(beats=4, items=(_chord_item("C", 1, 4),)),
        Bar(beats=4, items=(_chord_item("G", 1, 4, suffix="7"),)),
    )


@pytest.mark.parametrize(
    ("text", "message"),
    (
        ("C   ", "must contain at least one '\\|'"),
        ("|C   |    |", "cells must not be blank"),
        ("|C   |G7  ", "start and end with '\\|'"),
    ),
)
def test_parse_canonical_section_row_rejects_invalid_input(text: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        parse_canonical_section_row(text, beats=4)


@pytest.mark.parametrize(
    ("text", "root_lexeme", "suffix", "bass_lexeme"),
    (
        ("C", "C", "", None),
        ("Bbmaj7", "Bb", "maj7", None),
        ("Dbmaj7/Gb", "Db", "maj7", "Gb"),
        ("Eb7/Bb", "Eb", "7", "Bb"),
        ("G7Am", "G", "7Am", None),
        ("C#maj7/Bb", "C#", "maj7", "Bb"),
        ("Ksus/L", "K", "sus", "L"),
    ),
)
def test_parse_chord_token_examples(
    text: str, root_lexeme: str, suffix: str, bass_lexeme: str | None
) -> None:
    chord = parse_chord_token(text)

    _assert_chord_symbol(
        chord,
        root_lexeme=root_lexeme,
        suffix=suffix,
        bass_lexeme=bass_lexeme,
    )


def test_parser_functions_are_exposed_from_package_root() -> None:
    assert chord_charts.parse_chord_token is parse_chord_token
    assert chord_charts.parse_canonical_bar_cell is parse_canonical_bar_cell
    assert chord_charts.parse_section_header is parse_section_header
    assert chord_charts.parse_form_header is parse_form_header
    assert chord_charts.parse_source_blocks is parse_source_blocks
    assert chord_charts.parse_canonical_section_row is parse_canonical_section_row


@pytest.mark.parametrize(
    ("text", "message"),
    (
        ("", "must not be empty"),
        ("-", "not a chord token"),
        ("Q7", "supported note lexeme"),
        ("/C", "root note is missing"),
        ("C/", "bass note is missing"),
        ("//", "bass note is missing"),
        ("C/Gsus", "slash chord bass must be a supported note lexeme"),
        ("C//D", "chord suffix must not contain '/'"),
        ("C/ma/G", "chord suffix must not contain '/'"),
        ("C G", "must not contain whitespace"),
    ),
)
def test_parse_chord_token_rejects_invalid_input(text: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        parse_chord_token(text)


@given(case=_chord_token_cases())
def test_parse_chord_token_preserves_root_suffix_and_optional_bass(
    case: tuple[str, str, str | None]
) -> None:
    root_lexeme, suffix, bass_lexeme = case
    text = f"{root_lexeme}{suffix}"
    if bass_lexeme is not None:
        text = f"{text}/{bass_lexeme}"

    chord = parse_chord_token(text)

    _assert_chord_symbol(
        chord,
        root_lexeme=root_lexeme,
        suffix=suffix,
        bass_lexeme=bass_lexeme,
    )


def test_parse_canonical_bar_cell_accepts_single_chord_covering_bar() -> None:
    bar = parse_canonical_bar_cell("C   ", beats=4)

    assert bar == Bar(beats=4, items=(_chord_item("C", 1, 4),))


def test_parse_canonical_bar_cell_accepts_two_beat_half_bar_chords() -> None:
    bar = parse_canonical_bar_cell("Dm7     G7      ", beats=4)

    assert bar == Bar(
        beats=4,
        items=(
            _chord_item("D", 1, 2, suffix="m7"),
            _chord_item("G", 3, 2, suffix="7"),
        ),
    )


def test_parse_canonical_bar_cell_accepts_initial_carry() -> None:
    bar = parse_canonical_bar_cell("-       G7      ", beats=4)

    assert bar == Bar(
        beats=4,
        items=(
            CarryItem(start_beat=1, duration_beats=2),
            _chord_item("G", 3, 2, suffix="7"),
        ),
    )


def test_parse_canonical_bar_cell_accepts_full_bar_carry() -> None:
    bar = parse_canonical_bar_cell("-   ", beats=4)

    assert bar == Bar(beats=4, items=(CarryItem(start_beat=1, duration_beats=4),))


def test_parse_canonical_bar_cell_accepts_three_four_split() -> None:
    bar = parse_canonical_bar_cell("Am D7    ", beats=3)

    assert bar == Bar(
        beats=3,
        items=(
            _chord_item("A", 1, 1, suffix="m"),
            _chord_item("D", 2, 2, suffix="7"),
        ),
    )


def test_parse_canonical_bar_cell_accepts_accidental_spellings() -> None:
    bar = parse_canonical_bar_cell("Dbmaj7    Gb7       ", beats=4)

    assert bar == Bar(
        beats=4,
        items=(
            _chord_item("Db", 1, 2, suffix="maj7"),
            _chord_item("Gb", 3, 2, suffix="7"),
        ),
    )


@pytest.mark.parametrize(
    ("text", "beats", "message"),
    (
        ("C  ", 4, "not divisible by beats"),
        ("C\t  ", 4, "ASCII spaces"),
        ("    ", 4, "must contain at least one token"),
        ("/C  ", 2, "root note is missing"),
        (" C    ", 2, "beat boundary"),
        ("C - ", 4, "carry items may only appear first"),
    ),
)
def test_parse_canonical_bar_cell_rejects_invalid_input(
    text: str, beats: int, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        parse_canonical_bar_cell(text, beats=beats)


@given(bar=strategies.valid_bars())
def test_parse_canonical_bar_cell_round_trips_generated_valid_bars(bar: Bar) -> None:
    text = _render_canonical_bar_cell(bar)

    assert parse_canonical_bar_cell(text, beats=bar.beats) == bar


@given(bar=_canonical_bars())
def test_parse_canonical_bar_cell_round_trips_generated_canonical_parser_bars(
    bar: Bar,
) -> None:
    text = _render_canonical_bar_cell(bar)

    assert parse_canonical_bar_cell(text, beats=bar.beats) == bar


@given(case=_canonical_section_row_cases())
def test_parse_canonical_section_row_round_trips_generated_canonical_rows(
    case: tuple[int, tuple[Bar, ...], str]
) -> None:
    beats, bars, leading_indent = case
    text = _render_canonical_section_row(bars, leading_indent=leading_indent)

    assert parse_canonical_section_row(text, beats=beats) == bars
