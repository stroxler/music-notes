from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import final

from chord_charts.notes import is_pitch_class, pitch_class_for_lexeme


@final
@dataclass(frozen=True, slots=True)
class TextRange:
    start_byte: int
    end_byte: int

    def __post_init__(self) -> None:
        if self.start_byte < 0:
            raise ValueError("start_byte must be non-negative")
        if self.end_byte < self.start_byte:
            raise ValueError("end_byte must be greater than or equal to start_byte")

    @classmethod
    def synthetic(cls) -> TextRange:
        return cls(0, 0)


@final
@dataclass(frozen=True, slots=True)
class Meter:
    numerator: int
    denominator: int = 4
    span: TextRange = field(default_factory=TextRange.synthetic)

    def __post_init__(self) -> None:
        if self.numerator < 1:
            raise ValueError("meter numerator must be positive")
        if self.denominator != 4:
            raise ValueError("only quarter-note meters are supported")


@final
@dataclass(frozen=True, slots=True)
class ChordSymbol:
    root_pc: int
    suffix: str
    root_lexeme: str
    bass_pc: int | None = None
    bass_lexeme: str | None = None
    span: TextRange = field(default_factory=TextRange.synthetic)

    def __post_init__(self) -> None:
        _validate_pitch_class(self.root_pc, field_name="root_pc")
        if pitch_class_for_lexeme(self.root_lexeme) != self.root_pc:
            raise ValueError("root_lexeme does not match root_pc")

        if (self.bass_pc is None) != (self.bass_lexeme is None):
            raise ValueError("bass_pc and bass_lexeme must either both be set or both be None")

        if self.bass_pc is None or self.bass_lexeme is None:
            return

        _validate_pitch_class(self.bass_pc, field_name="bass_pc")
        if pitch_class_for_lexeme(self.bass_lexeme) != self.bass_pc:
            raise ValueError("bass_lexeme does not match bass_pc")


@final
@dataclass(frozen=True, slots=True)
class CarryItem:
    start_beat: int
    duration_beats: int
    span: TextRange = field(default_factory=TextRange.synthetic)


@final
@dataclass(frozen=True, slots=True)
class ChordItem:
    chord: ChordSymbol
    start_beat: int
    duration_beats: int
    span: TextRange = field(default_factory=TextRange.synthetic)


@final
@dataclass(frozen=True, slots=True)
class Bar:
    beats: int
    items: tuple[CarryItem | ChordItem, ...]
    span: TextRange = field(default_factory=TextRange.synthetic)

    def __post_init__(self) -> None:
        if self.beats < 1:
            raise ValueError("bar beats must be positive")
        object.__setattr__(self, "items", tuple(self.items))


BarItem = CarryItem | ChordItem


@final
@dataclass(frozen=True, slots=True)
class MetadataField:
    name: str
    value: str


@final
@dataclass(frozen=True, slots=True)
class SectionBody:
    rows: tuple[tuple[Bar, ...], ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "rows", _normalize_non_empty_rows(self.rows, context="section body"))


@final
@dataclass(frozen=True, slots=True)
class SectionEnding:
    name: str
    rows: tuple[tuple[Bar, ...], ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "rows",
            _normalize_non_empty_rows(self.rows, context="section ending"),
        )


@final
@dataclass(frozen=True, slots=True)
class Section:
    name: str
    body: SectionBody
    endings: tuple[SectionEnding, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "endings", tuple(self.endings))


@final
@dataclass(frozen=True, slots=True)
class FormText:
    text: str


@final
@dataclass(frozen=True, slots=True)
class FormSectionRef:
    name: str
    ending: str | None = None


FormItem = FormText | FormSectionRef


@final
@dataclass(frozen=True, slots=True)
class Form:
    name: str | None = None
    items: tuple[FormItem, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "items", tuple(self.items))


@final
@dataclass(frozen=True, slots=True)
class Document:
    meter: Meter
    metadata: tuple[MetadataField, ...] = ()
    sections: tuple[Section, ...] = ()
    forms: tuple[Form, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", tuple(self.metadata))
        object.__setattr__(self, "sections", tuple(self.sections))
        object.__setattr__(self, "forms", tuple(self.forms))


def _validate_pitch_class(value: int, *, field_name: str) -> None:
    if not is_pitch_class(value):
        raise ValueError(f"{field_name} must be in 0..11, got {value}")


def _normalize_rows(rows: Iterable[Iterable[Bar]]) -> tuple[tuple[Bar, ...], ...]:
    normalized_rows = tuple(tuple(row) for row in rows)
    if any(not row for row in normalized_rows):
        raise ValueError("section rows must contain at least one bar")
    return normalized_rows


def _normalize_non_empty_rows(
    rows: Iterable[Iterable[Bar]], *, context: str
) -> tuple[tuple[Bar, ...], ...]:
    normalized_rows = _normalize_rows(rows)
    if not normalized_rows:
        raise ValueError(f"{context} must contain at least one row")
    return normalized_rows
