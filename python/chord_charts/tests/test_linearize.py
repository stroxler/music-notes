from __future__ import annotations

import pytest

import chord_charts
from chord_charts import (
    Bar,
    ChordItem,
    ChordSymbol,
    Document,
    Form,
    FormSectionRef,
    FormText,
    LinearBar,
    Meter,
    Section,
    SectionBody,
    SectionEnding,
    linearize_canonical_form,
)
from chord_charts.notes import pitch_class_for_lexeme


def _bar(lexeme: str) -> Bar:
    return Bar(
        beats=4,
        items=(
            ChordItem(
                chord=ChordSymbol(
                    root_pc=pitch_class_for_lexeme(lexeme),
                    suffix="",
                    root_lexeme=lexeme,
                ),
                start_beat=1,
                duration_beats=4,
            ),
        ),
    )


def test_linearize_canonical_form_prefers_plain_form_and_ignores_text() -> None:
    a_bar = _bar("C")
    b_bar = _bar("F")
    document = Document(
        meter=Meter(numerator=4),
        sections=(
            Section(name="A", body=SectionBody(rows=((a_bar,),))),
            Section(name="B", body=SectionBody(rows=((b_bar,),))),
        ),
        forms=(
            Form(name="lyrics", items=(FormSectionRef(name="B"),)),
            Form(items=(FormText("count "), FormSectionRef(name="A"))),
        ),
    )

    assert linearize_canonical_form(document) == (
        LinearBar(
            play=FormSectionRef(name="A"),
            source_section="A",
            source_part="body",
            source_bar_index=0,
            bar=a_bar,
        ),
    )


def test_linearize_canonical_form_falls_back_to_first_named_form() -> None:
    a_bar = _bar("C")
    b_bar = _bar("F")
    document = Document(
        meter=Meter(numerator=4),
        sections=(
            Section(name="A", body=SectionBody(rows=((a_bar,),))),
            Section(name="B", body=SectionBody(rows=((b_bar,),))),
        ),
        forms=(
            Form(name="lyrics", items=(FormSectionRef(name="A"),)),
            Form(name="roman", items=(FormSectionRef(name="B"),)),
        ),
    )

    assert linearize_canonical_form(document) == (
        LinearBar(
            play=FormSectionRef(name="A"),
            source_section="A",
            source_part="body",
            source_bar_index=0,
            bar=a_bar,
        ),
    )


def test_linearize_canonical_form_returns_empty_for_document_without_forms() -> None:
    assert linearize_canonical_form(Document(meter=Meter(numerator=4))) == ()


def test_linearize_canonical_form_expands_body_only_reference_row_major() -> None:
    first_bar = _bar("C")
    second_bar = _bar("F")
    third_bar = _bar("G")
    document = Document(
        meter=Meter(numerator=4),
        sections=(
            Section(
                name="A",
                body=SectionBody(rows=((first_bar, second_bar), (third_bar,))),
            ),
        ),
        forms=(Form(items=(FormSectionRef(name="A"),)),),
    )

    assert linearize_canonical_form(document) == (
        LinearBar(
            play=FormSectionRef(name="A"),
            source_section="A",
            source_part="body",
            source_bar_index=0,
            bar=first_bar,
        ),
        LinearBar(
            play=FormSectionRef(name="A"),
            source_section="A",
            source_part="body",
            source_bar_index=1,
            bar=second_bar,
        ),
        LinearBar(
            play=FormSectionRef(name="A"),
            source_section="A",
            source_part="body",
            source_bar_index=2,
            bar=third_bar,
        ),
    )


def test_linearize_canonical_form_expands_body_then_selected_ending_with_provenance() -> None:
    body_bar = _bar("C")
    ignored_ending_bar = _bar("F")
    ending_bar_one = _bar("G")
    ending_bar_two = _bar("A")
    document = Document(
        meter=Meter(numerator=4),
        sections=(
            Section(
                name="A",
                body=SectionBody(rows=((body_bar,),)),
                endings=(
                    SectionEnding(name="1", rows=((ignored_ending_bar,),)),
                    SectionEnding(name="2", rows=((ending_bar_one, ending_bar_two),)),
                ),
            ),
        ),
        forms=(Form(items=(FormSectionRef(name="A", ending="2"),)),),
    )

    assert linearize_canonical_form(document) == (
        LinearBar(
            play=FormSectionRef(name="A", ending="2"),
            source_section="A",
            source_part="body",
            source_bar_index=0,
            bar=body_bar,
        ),
        LinearBar(
            play=FormSectionRef(name="A", ending="2"),
            source_section="A",
            source_part="ending",
            source_bar_index=0,
            source_ending="2",
            bar=ending_bar_one,
        ),
        LinearBar(
            play=FormSectionRef(name="A", ending="2"),
            source_section="A",
            source_part="ending",
            source_bar_index=1,
            source_ending="2",
            bar=ending_bar_two,
        ),
    )


def test_linearize_canonical_form_rejects_unknown_section() -> None:
    document = Document(
        meter=Meter(numerator=4),
        sections=(Section(name="A", body=SectionBody(rows=((_bar("C"),),))),),
        forms=(Form(items=(FormSectionRef(name="B"),)),),
    )

    with pytest.raises(ValueError, match=r"canonical form references unknown section \[B\]"):
        linearize_canonical_form(document)


def test_linearize_canonical_form_requires_ending_when_section_has_endings() -> None:
    document = Document(
        meter=Meter(numerator=4),
        sections=(
            Section(
                name="A",
                body=SectionBody(rows=((_bar("C"),),)),
                endings=(SectionEnding(name="1", rows=((_bar("G"),),)),),
            ),
        ),
        forms=(Form(items=(FormSectionRef(name="A"),)),),
    )

    with pytest.raises(
        ValueError,
        match=r"canonical form must reference section 'A' as \[A:ending\] because the section has endings",
    ):
        linearize_canonical_form(document)


@pytest.mark.parametrize(
    ("document", "message"),
    (
        (
            Document(
                meter=Meter(numerator=4),
                sections=(Section(name="A", body=SectionBody(rows=((_bar("C"),),))),),
                forms=(Form(items=(FormSectionRef(name="A", ending="1"),)),),
            ),
            r"canonical form must reference section 'A' as \[A\] because the section has no endings",
        ),
        (
            Document(
                meter=Meter(numerator=4),
                sections=(
                    Section(
                        name="A",
                        body=SectionBody(rows=((_bar("C"),),)),
                        endings=(SectionEnding(name="1", rows=((_bar("G"),),)),),
                    ),
                ),
                forms=(Form(items=(FormSectionRef(name="A", ending="2"),)),),
            ),
            r"canonical form references unknown ending \[A:2\]",
        ),
    ),
)
def test_linearize_canonical_form_rejects_invalid_ending_references(
    document: Document, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        linearize_canonical_form(document)


def test_linearize_api_is_exposed_from_package_root() -> None:
    assert chord_charts.LinearBar is LinearBar
    assert chord_charts.linearize_canonical_form is linearize_canonical_form
