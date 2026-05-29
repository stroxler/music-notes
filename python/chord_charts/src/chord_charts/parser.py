from __future__ import annotations

import re

from chord_charts.model import Bar, CarryItem, ChordItem, ChordSymbol
from chord_charts.notes import ACCEPTED_INPUT_LEXEMES, pitch_class_for_lexeme
from chord_charts.validation import assert_valid_bar

__all__ = ["parse_chord_token", "parse_canonical_bar_cell"]

_NOTE_LEXEMES_BY_LENGTH = tuple(sorted(ACCEPTED_INPUT_LEXEMES, key=len, reverse=True))


def parse_chord_token(text: str) -> ChordSymbol:
    if not text:
        raise ValueError("chord token must not be empty")
    if any(character.isspace() for character in text):
        raise ValueError("chord token must not contain whitespace")
    if text == "-":
        raise ValueError("carry token is not a chord token")

    body = text
    bass_lexeme: str | None = None
    bass_pc: int | None = None

    if "/" in text:
        body, bass_text = text.rsplit("/", 1)
        if not body:
            raise ValueError("slash chord root note is missing before '/'")
        if not bass_text:
            raise ValueError("slash chord bass note is missing")
        bass_lexeme, bass_pc = _parse_note_lexeme(bass_text, context="slash chord bass")
        if bass_lexeme != bass_text:
            raise ValueError("slash chord bass must be a supported note lexeme")

    root_lexeme, root_pc = _parse_note_lexeme(body, context="chord token")
    suffix = body[len(root_lexeme) :]
    if "/" in suffix:
        raise ValueError("chord suffix must not contain '/'")

    return ChordSymbol(
        root_pc=root_pc,
        suffix=suffix,
        root_lexeme=root_lexeme,
        bass_pc=bass_pc,
        bass_lexeme=bass_lexeme,
    )


def parse_canonical_bar_cell(text: str, *, beats: int) -> Bar:
    if beats < 1:
        raise ValueError("beats must be positive")
    if any(character.isspace() and character != " " for character in text):
        raise ValueError("canonical bar cells only allow ASCII spaces as whitespace")

    width = len(text)
    if width % beats != 0:
        raise ValueError(f"bar cell width {width} is not divisible by beats {beats}")

    token_columns = [(match.group(), match.start()) for match in re.finditer(r"[^ ]+", text)]
    if not token_columns:
        raise ValueError("canonical bar cell must contain at least one token")

    slot_width = width // beats
    items: list[CarryItem | ChordItem] = []

    for index, (token, start_column) in enumerate(token_columns):
        if start_column % slot_width != 0:
            raise ValueError(
                f"token {token!r} starts at column {start_column}, not on a beat boundary"
            )

        start_beat = (start_column // slot_width) + 1
        if index + 1 < len(token_columns):
            next_start_column = token_columns[index + 1][1]
            max_token_width = next_start_column - start_column - 1
            if len(token) > max_token_width:
                raise ValueError(
                    f"token {token!r} must leave at least one space before the next token"
                )
            duration_beats = (next_start_column - start_column) // slot_width
        else:
            max_token_width = width - start_column
            if len(token) > max_token_width:
                raise ValueError(f"token {token!r} does not fit before the end of the bar")
            duration_beats = beats - start_beat + 1

        if token == "-":
            if index != 0:
                raise ValueError("carry items may only appear first")
            items.append(CarryItem(start_beat=start_beat, duration_beats=duration_beats))
            continue

        items.append(
            ChordItem(
                chord=parse_chord_token(token),
                start_beat=start_beat,
                duration_beats=duration_beats,
            )
        )

    bar = Bar(beats=beats, items=tuple(items))
    assert_valid_bar(bar)
    return bar


def _parse_note_lexeme(text: str, *, context: str) -> tuple[str, int]:
    for lexeme in _NOTE_LEXEMES_BY_LENGTH:
        if text.startswith(lexeme):
            return lexeme, pitch_class_for_lexeme(lexeme)

    raise ValueError(f"{context} must start with a supported note lexeme: {text!r}")
