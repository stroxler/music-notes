from __future__ import annotations

import chord_charts
from hypothesis import given, strategies as st

from chord_charts import (
    Bar,
    CarryItem,
    ChordItem,
    ChordSymbol,
    Document,
    Form,
    FormSectionRef,
    MetadataField,
    Meter,
    NoteSpellingPolicy,
    Section,
    SectionBody,
    SectionEnding,
    TextRange,
    linearize_canonical_form,
    render_pitch_class,
    respell_chord_symbol,
    respell_document,
)
from chord_charts.notes import pitch_class_for_lexeme
from . import strategies


def _chord_item(
    root_lexeme: str,
    *,
    start_beat: int = 1,
    duration_beats: int = 4,
    suffix: str = "",
    bass_lexeme: str | None = None,
    span: TextRange | None = None,
) -> ChordItem:
    return ChordItem(
        chord=ChordSymbol(
            root_pc=pitch_class_for_lexeme(root_lexeme),
            suffix=suffix,
            root_lexeme=root_lexeme,
            bass_pc=None if bass_lexeme is None else pitch_class_for_lexeme(bass_lexeme),
            bass_lexeme=bass_lexeme,
            span=TextRange.synthetic() if span is None else span,
        ),
        start_beat=start_beat,
        duration_beats=duration_beats,
        span=TextRange.synthetic() if span is None else span,
    )


def _first_chord(bar: Bar) -> ChordSymbol:
    for item in bar.items:
        if isinstance(item, ChordItem):
            return item.chord

    raise AssertionError("expected bar to contain a chord")


def _first_chord_item(bar: Bar) -> ChordItem:
    for item in bar.items:
        if isinstance(item, ChordItem):
            return item

    raise AssertionError("expected bar to contain a chord")


def test_respell_chord_symbol_rewrites_note_lexemes_only() -> None:
    span = TextRange(3, 11)
    chord = ChordSymbol(
        root_pc=10,
        suffix="7sus",
        root_lexeme="J",
        bass_pc=1,
        bass_lexeme="K",
        span=span,
    )

    assert respell_chord_symbol(chord, policy="accidental(sharp-heavy)") == ChordSymbol(
        root_pc=10,
        suffix="7sus",
        root_lexeme="Bb",
        bass_pc=1,
        bass_lexeme="C#",
        span=span,
    )


@given(
    root_lexeme=strategies.accepted_note_lexemes(),
    bass_lexeme=st.one_of(st.none(), strategies.accepted_note_lexemes()),
    suffix=st.sampled_from(("", "m", "7", "maj7", "sus")),
    policy=strategies.note_spelling_policies(),
)
def test_respell_chord_symbol_preserves_non_spelling_fields(
    root_lexeme: str,
    bass_lexeme: str | None,
    suffix: str,
    policy: NoteSpellingPolicy,
) -> None:
    chord = ChordSymbol(
        root_pc=pitch_class_for_lexeme(root_lexeme),
        suffix=suffix,
        root_lexeme=root_lexeme,
        bass_pc=None if bass_lexeme is None else pitch_class_for_lexeme(bass_lexeme),
        bass_lexeme=bass_lexeme,
        span=TextRange(3, 11),
    )

    respelled = respell_chord_symbol(chord, policy=policy)

    assert respelled.root_pc == chord.root_pc
    assert respelled.bass_pc == chord.bass_pc
    assert respelled.suffix == chord.suffix
    assert respelled.span == chord.span
    assert respelled.root_lexeme == render_pitch_class(chord.root_pc, policy)
    assert respelled.bass_lexeme == (
        None if chord.bass_pc is None else render_pitch_class(chord.bass_pc, policy)
    )


def test_respell_document_rewrites_section_bodies_and_endings_only() -> None:
    carry = CarryItem(start_beat=1, duration_beats=1, span=TextRange(20, 21))
    body_chord = _chord_item(
        "K",
        start_beat=2,
        duration_beats=3,
        suffix="maj7",
        span=TextRange(21, 26),
    )
    ending_chord = _chord_item(
        "J",
        suffix="7",
        bass_lexeme="H",
        span=TextRange(30, 35),
    )
    body_bar = Bar(
        beats=4,
        items=(carry, body_chord),
        span=TextRange(20, 26),
    )
    ending_bar = Bar(
        beats=4,
        items=(ending_chord,),
        span=TextRange(30, 35),
    )
    document = Document(
        meter=Meter(numerator=4, span=TextRange(0, 3)),
        metadata=(MetadataField(name="title", value="Respell"),),
        sections=(
            Section(
                name="A",
                body=SectionBody(rows=((body_bar,),)),
                endings=(SectionEnding(name="1", rows=((ending_bar,),)),),
            ),
        ),
        forms=(Form(items=(FormSectionRef(name="A", ending="1"),)),),
    )

    respelled = respell_document(document, policy="accidental(flat-heavy)")

    assert respelled.meter == document.meter
    assert respelled.metadata == document.metadata
    assert respelled.forms == document.forms
    assert respelled.sections[0].name == "A"
    assert respelled.sections[0].endings[0].name == "1"
    assert respelled.sections[0].body.rows[0][0].items[0] is carry
    body_item = _first_chord_item(respelled.sections[0].body.rows[0][0])
    assert body_item.start_beat == body_chord.start_beat
    assert body_item.duration_beats == body_chord.duration_beats
    assert body_item.span == body_chord.span
    assert body_item.chord.root_pc == body_chord.chord.root_pc
    assert body_item.chord.root_lexeme == "Db"
    assert body_item.chord.suffix == "maj7"
    assert _first_chord(respelled.sections[0].endings[0].rows[0][0]).root_lexeme == "Bb"
    assert _first_chord(respelled.sections[0].endings[0].rows[0][0]).bass_lexeme == "F#"


def test_respell_document_is_idempotent_for_matching_policy() -> None:
    document = Document(
        meter=Meter(numerator=4),
        sections=(
            Section(
                name="A",
                body=SectionBody(
                    rows=(
                        (
                            Bar(
                                beats=4,
                                items=(_chord_item("Db", suffix="maj7"),),
                            ),
                        ),
                    )
                ),
                endings=(
                    SectionEnding(
                        name="1",
                        rows=(
                            (
                                Bar(
                                    beats=4,
                                    items=(_chord_item("Bb", bass_lexeme="F#"),),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
        forms=(Form(items=(FormSectionRef(name="A", ending="1"),)),),
    )

    assert respell_document(document, policy="accidental(flat-heavy)") == document


def test_linearization_provenance_is_unchanged_after_respelling() -> None:
    document = Document(
        meter=Meter(numerator=4),
        sections=(
            Section(
                name="A",
                body=SectionBody(rows=((Bar(beats=4, items=(_chord_item("K"),)),),)),
                endings=(
                    SectionEnding(
                        name="2",
                        rows=((Bar(beats=4, items=(_chord_item("J", bass_lexeme="H"),)),),),
                    ),
                ),
            ),
        ),
        forms=(Form(items=(FormSectionRef(name="A", ending="2"),)),),
    )

    original = linearize_canonical_form(document)
    respelled = linearize_canonical_form(
        respell_document(document, policy="accidental(flat-heavy)")
    )

    assert tuple(
        (
            linear_bar.play,
            linear_bar.source_section,
            linear_bar.source_part,
            linear_bar.source_ending,
            linear_bar.source_bar_index,
        )
        for linear_bar in respelled
    ) == tuple(
        (
            linear_bar.play,
            linear_bar.source_section,
            linear_bar.source_part,
            linear_bar.source_ending,
            linear_bar.source_bar_index,
        )
        for linear_bar in original
    )
    assert tuple(_first_chord(linear_bar.bar).root_lexeme for linear_bar in respelled) == (
        "Db",
        "Bb",
    )
    assert _first_chord(respelled[1].bar).bass_lexeme == "F#"


def test_transform_api_is_exposed_from_package_root() -> None:
    assert chord_charts.respell_chord_symbol is respell_chord_symbol
    assert chord_charts.respell_document is respell_document
