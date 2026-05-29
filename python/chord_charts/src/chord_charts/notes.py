from __future__ import annotations

from typing import Final, Literal

PitchClass = int
NoteSpellingPolicy = Literal[
    "hij",
    "accidental(flat-heavy)",
    "accidental(sharp-heavy)",
]

_LEXEME_TO_PITCH_CLASS: Final[dict[str, PitchClass]] = {
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
ACCEPTED_INPUT_LEXEMES: Final[tuple[str, ...]] = tuple(_LEXEME_TO_PITCH_CLASS)

_RENDER_TABLES: Final[dict[NoteSpellingPolicy, tuple[str, ...]]] = {
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
NOTE_SPELLING_POLICIES: Final[tuple[NoteSpellingPolicy, ...]] = tuple(_RENDER_TABLES)


def is_pitch_class(value: int) -> bool:
    return 0 <= value <= 11


def pitch_class_for_lexeme(lexeme: str) -> PitchClass:
    try:
        return _LEXEME_TO_PITCH_CLASS[lexeme]
    except KeyError as exc:
        raise ValueError(f"unsupported note lexeme: {lexeme!r}") from exc


def render_pitch_class(pitch_class: PitchClass, policy: NoteSpellingPolicy) -> str:
    if not is_pitch_class(pitch_class):
        raise ValueError(f"pitch class must be in 0..11, got {pitch_class}")

    try:
        render_table = _RENDER_TABLES[policy]
    except KeyError as exc:
        raise ValueError(f"unsupported note spelling policy: {policy!r}") from exc

    return render_table[pitch_class]


def respell_note_lexeme(lexeme: str, policy: NoteSpellingPolicy) -> str:
    return render_pitch_class(pitch_class_for_lexeme(lexeme), policy)
