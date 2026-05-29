from __future__ import annotations

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


def _validate_pitch_class(value: int, *, field_name: str) -> None:
    if not is_pitch_class(value):
        raise ValueError(f"{field_name} must be in 0..11, got {value}")
