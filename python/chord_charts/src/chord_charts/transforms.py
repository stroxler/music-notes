from __future__ import annotations

from dataclasses import replace

from chord_charts.model import (
    Bar,
    BarItem,
    CarryItem,
    ChordSymbol,
    Document,
    Section,
    SectionEnding,
)
from chord_charts.notes import NoteSpellingPolicy, render_pitch_class


def respell_chord_symbol(chord: ChordSymbol, *, policy: NoteSpellingPolicy) -> ChordSymbol:
    root_lexeme = render_pitch_class(chord.root_pc, policy)
    bass_lexeme = (
        None if chord.bass_pc is None else render_pitch_class(chord.bass_pc, policy)
    )

    if chord.root_lexeme == root_lexeme and chord.bass_lexeme == bass_lexeme:
        return chord

    return replace(chord, root_lexeme=root_lexeme, bass_lexeme=bass_lexeme)


def respell_document(document: Document, *, policy: NoteSpellingPolicy) -> Document:
    return replace(
        document,
        sections=tuple(_respell_section(section, policy=policy) for section in document.sections),
    )


def _respell_section(section: Section, *, policy: NoteSpellingPolicy) -> Section:
    return replace(
        section,
        body=replace(section.body, rows=_respell_rows(section.body.rows, policy=policy)),
        endings=tuple(_respell_section_ending(ending, policy=policy) for ending in section.endings),
    )


def _respell_section_ending(
    ending: SectionEnding, *, policy: NoteSpellingPolicy
) -> SectionEnding:
    return replace(ending, rows=_respell_rows(ending.rows, policy=policy))


def _respell_rows(
    rows: tuple[tuple[Bar, ...], ...], *, policy: NoteSpellingPolicy
) -> tuple[tuple[Bar, ...], ...]:
    return tuple(tuple(_respell_bar(bar, policy=policy) for bar in row) for row in rows)


def _respell_bar(bar: Bar, *, policy: NoteSpellingPolicy) -> Bar:
    return replace(bar, items=tuple(_respell_bar_item(item, policy=policy) for item in bar.items))


def _respell_bar_item(item: BarItem, *, policy: NoteSpellingPolicy) -> BarItem:
    if isinstance(item, CarryItem):
        return item

    chord = respell_chord_symbol(item.chord, policy=policy)
    if chord == item.chord:
        return item

    return replace(item, chord=chord)
