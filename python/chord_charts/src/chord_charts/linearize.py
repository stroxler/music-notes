from __future__ import annotations

from typing import Literal

from chord_charts.model import Bar, Document, Form, FormSectionRef, LinearBar, Section, SectionEnding


def linearize_canonical_form(document: Document) -> tuple[LinearBar, ...]:
    canonical_form = _canonical_form(document)
    if canonical_form is None:
        return ()

    sections_by_name = {section.name: section for section in document.sections}
    return tuple(
        linear_bar
        for ref in _form_reference_sequence(canonical_form)
        for linear_bar in _linearize_ref(play=ref, sections_by_name=sections_by_name)
    )


def _canonical_form(document: Document) -> Form | None:
    for form in document.forms:
        if form.name is None:
            return form

    if document.forms:
        return document.forms[0]
    return None


def _form_reference_sequence(form: Form) -> tuple[FormSectionRef, ...]:
    return tuple(item for item in form.items if isinstance(item, FormSectionRef))


def _linearize_ref(
    *, play: FormSectionRef, sections_by_name: dict[str, Section]
) -> tuple[LinearBar, ...]:
    section = sections_by_name.get(play.name)
    if section is None:
        raise ValueError(f"canonical form references unknown section {_render_ref(play)}")

    if play.ending is None:
        if section.endings:
            raise ValueError(
                f"canonical form must reference section {section.name!r} as "
                f"[{section.name}:ending] because the section has endings"
            )
        return _linearize_rows(
            play=play,
            section_name=section.name,
            source_part="body",
            source_ending=None,
            rows=section.body.rows,
        )

    ending = _ending_by_name(section=section, ending_name=play.ending)
    if ending is None:
        if section.endings:
            raise ValueError(f"canonical form references unknown ending {_render_ref(play)}")
        raise ValueError(
            f"canonical form must reference section {section.name!r} as "
            f"[{section.name}] because the section has no endings"
        )

    return _linearize_rows(
        play=play,
        section_name=section.name,
        source_part="body",
        source_ending=None,
        rows=section.body.rows,
    ) + _linearize_rows(
        play=play,
        section_name=section.name,
        source_part="ending",
        source_ending=ending.name,
        rows=ending.rows,
    )


def _ending_by_name(*, section: Section, ending_name: str) -> SectionEnding | None:
    return next((ending for ending in section.endings if ending.name == ending_name), None)


def _linearize_rows(
    *,
    play: FormSectionRef,
    section_name: str,
    source_part: Literal["body", "ending"],
    source_ending: str | None,
    rows: tuple[tuple[Bar, ...], ...],
) -> tuple[LinearBar, ...]:
    return tuple(
        LinearBar(
            play=play,
            source_section=section_name,
            source_part=source_part,
            source_bar_index=source_bar_index,
            source_ending=source_ending,
            bar=bar,
        )
        for source_bar_index, bar in enumerate(bar for row in rows for bar in row)
    )


def _render_ref(ref: FormSectionRef) -> str:
    if ref.ending is None:
        return f"[{ref.name}]"
    return f"[{ref.name}:{ref.ending}]"
