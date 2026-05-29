from __future__ import annotations

import re
from dataclasses import dataclass
from typing import final

from chord_charts.model import (
    Bar,
    CarryItem,
    ChordItem,
    ChordSymbol,
    Document,
    Form,
    FormItem,
    FormSectionRef,
    FormText,
    MetadataField,
    Meter,
    Section,
    SectionBody,
    SectionEnding,
)
from chord_charts.notes import ACCEPTED_INPUT_LEXEMES, pitch_class_for_lexeme
from chord_charts.validation import assert_valid_bar

__all__ = [
    "parse_document",
    "FormItem",
    "FormHeader",
    "FormSectionRef",
    "FormText",
    "ParsedBlock",
    "ParsedFormBlock",
    "ParsedSectionBlock",
    "SectionHeader",
    "parse_canonical_bar_cell",
    "parse_canonical_section_row",
    "parse_chord_token",
    "parse_form_body_lines",
    "parse_form_header",
    "parse_source_blocks",
    "parse_section_header",
]

_IDENTIFIER_PATTERN = r"[A-Za-z0-9_-]+"
_NOTE_LEXEMES_BY_LENGTH = tuple(sorted(ACCEPTED_INPUT_LEXEMES, key=len, reverse=True))
_SECTION_HEADER_RE = re.compile(
    rf"^\[(?P<name>{_IDENTIFIER_PATTERN})(?::(?P<ending>{_IDENTIFIER_PATTERN}))?\]:$"
)
_FORM_HEADER_RE = re.compile(rf"^form(?:\[(?P<name>{_IDENTIFIER_PATTERN})\])?:$")
_FORM_REF_RE = re.compile(
    rf"^(?P<name>{_IDENTIFIER_PATTERN})(?::(?P<ending>{_IDENTIFIER_PATTERN}))?$"
)
_HEADER_LINE_RE = re.compile(rf"^(?P<name>{_IDENTIFIER_PATTERN}):(?P<value>.*)$")
_METER_RE = re.compile(r"^(?P<numerator>[1-9][0-9]*)/4$")


@final
@dataclass(frozen=True, slots=True)
class SectionHeader:
    name: str
    ending: str | None = None


@final
@dataclass(frozen=True, slots=True)
class FormHeader:
    name: str | None = None


@final
@dataclass(frozen=True, slots=True)
class ParsedSectionBlock:
    header: SectionHeader
    rows: tuple[tuple[Bar, ...], ...]


@final
@dataclass(frozen=True, slots=True)
class ParsedFormBlock:
    header: FormHeader
    body_lines: tuple[str, ...]


ParsedBlock = ParsedSectionBlock | ParsedFormBlock


def parse_section_header(text: str) -> SectionHeader:
    header = _match_section_header(text)
    if header is None:
        raise ValueError(f"invalid section header: {text!r}")
    return header


def parse_form_header(text: str) -> FormHeader:
    header = _match_form_header(text)
    if header is None:
        raise ValueError(f"invalid form header: {text!r}")
    return header


def parse_form_body_lines(body_lines: tuple[str, ...]) -> tuple[FormItem, ...]:
    source = "\n".join(body_lines)
    items: list[FormItem] = []
    text_buffer: list[str] = []
    index = 0

    while index < len(source):
        character = source[index]

        if character == "\\":
            decoded_character, next_index = _decode_form_text_escape(source, index)
            text_buffer.append(decoded_character)
            index = next_index
            continue

        if character == "[":
            ref_end = source.find("]", index + 1)
            if ref_end >= 0:
                ref = _parse_form_ref(source[index + 1 : ref_end])
                if ref is not None:
                    if text_buffer:
                        items.append(FormText("".join(text_buffer)))
                        text_buffer = []
                    items.append(ref)
                    index = ref_end + 1
                    continue

        text_buffer.append(character)
        index += 1

    if text_buffer:
        items.append(FormText("".join(text_buffer)))
    return tuple(items)


def parse_document(text: str) -> Document:
    meter, metadata, block_text = _parse_document_headers(text)
    return _build_document(
        meter=meter,
        metadata=metadata,
        blocks=parse_source_blocks(block_text, beats=meter.numerator),
    )


def parse_source_blocks(text: str, *, beats: int) -> tuple[ParsedBlock, ...]:
    blocks: list[ParsedBlock] = []
    current_header: SectionHeader | FormHeader | None = None
    current_body_lines: list[str] = []
    state = "start"

    for line in text.splitlines():
        header = _parse_block_header(line)
        if header is not None:
            if isinstance(header, SectionHeader):
                if state == "forms":
                    raise ValueError("section blocks must not appear after form blocks")
                state = "sections"
            else:
                if state == "start":
                    raise ValueError("form blocks must follow at least one section block")
                state = "forms"

            if current_header is not None:
                blocks.append(
                    _build_block(current_header, body_lines=tuple(current_body_lines), beats=beats)
                )
            current_header = header
            current_body_lines = []
            continue

        if current_header is None:
            if line.strip():
                raise ValueError("content before first section or form header")
            continue

        current_body_lines.append(line)

    if current_header is not None:
        blocks.append(_build_block(current_header, body_lines=tuple(current_body_lines), beats=beats))

    return tuple(blocks)


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


def parse_canonical_section_row(text: str, *, beats: int) -> tuple[Bar, ...]:
    stripped_text = text.strip()
    if not stripped_text:
        raise ValueError("section row must not be blank")
    if "|" not in stripped_text:
        raise ValueError("section row must contain at least one '|'")

    cells = stripped_text.split("|")
    if cells[0] != "" or cells[-1] != "":
        raise ValueError("section row must start and end with '|'")

    bar_cells = cells[1:-1]
    if any(not cell.strip() for cell in bar_cells):
        raise ValueError("section row cells must not be blank")

    return tuple(parse_canonical_bar_cell(cell, beats=beats) for cell in bar_cells)


def _parse_note_lexeme(text: str, *, context: str) -> tuple[str, int]:
    for lexeme in _NOTE_LEXEMES_BY_LENGTH:
        if text.startswith(lexeme):
            return lexeme, pitch_class_for_lexeme(lexeme)

    raise ValueError(f"{context} must start with a supported note lexeme: {text!r}")


def _build_block(
    header: SectionHeader | FormHeader, *, body_lines: tuple[str, ...], beats: int
) -> ParsedBlock:
    if isinstance(header, FormHeader):
        return ParsedFormBlock(header=header, body_lines=body_lines)

    rows = tuple(
        parse_canonical_section_row(line, beats=beats) for line in body_lines if line.strip()
    )
    if not rows:
        raise ValueError(f"section block {header.name!r} must contain at least one row")

    return ParsedSectionBlock(header=header, rows=rows)


def _parse_block_header(line: str) -> SectionHeader | FormHeader | None:
    return _match_section_header(line) or _match_form_header(line)


def _parse_document_headers(text: str) -> tuple[Meter, tuple[MetadataField, ...], str]:
    lines = text.splitlines()
    metadata: list[MetadataField] = []
    meter: Meter | None = None
    body_start_index = len(lines)

    for index, line in enumerate(lines):
        if _parse_block_header(line) is not None:
            body_start_index = index
            break

        if not line.strip():
            continue

        header = _parse_header_line(line)
        if header is None:
            raise ValueError(
                f"non-header line before first section or form header: {line!r}"
            )

        if header.name == "meter":
            if meter is not None:
                raise ValueError("duplicate meter header")
            meter = _parse_meter_value(header.value)
            continue

        metadata.append(header)

    if meter is None:
        meter = Meter(numerator=4)

    return meter, tuple(metadata), "\n".join(lines[body_start_index:])


def _parse_header_line(line: str) -> MetadataField | None:
    match = _HEADER_LINE_RE.fullmatch(line)
    if match is None:
        return None

    return MetadataField(name=match.group("name"), value=match.group("value").strip())


def _parse_meter_value(value: str) -> Meter:
    match = _METER_RE.fullmatch(value.strip())
    if match is None:
        raise ValueError(f"invalid meter header: {value!r}")

    return Meter(numerator=int(match.group("numerator")))


def _build_document(
    *,
    meter: Meter,
    metadata: tuple[MetadataField, ...],
    blocks: tuple[ParsedBlock, ...],
) -> Document:
    section_order: list[str] = []
    section_bodies: dict[str, SectionBody] = {}
    section_endings: dict[str, list[SectionEnding]] = {}
    forms: list[Form] = []
    seen_names: set[str | None] = set()

    for block in blocks:
        if isinstance(block, ParsedSectionBlock):
            section_name = block.header.name
            ending_name = block.header.ending

            if ending_name is None:
                if section_name in section_bodies:
                    raise ValueError(f"duplicate section body: {section_name!r}")
                section_order.append(section_name)
                section_bodies[section_name] = SectionBody(rows=block.rows)
                section_endings[section_name] = []
                continue

            endings = section_endings.get(section_name)
            if endings is None:
                raise ValueError(
                    f"section ending {section_name!r}:{ending_name!r} must follow its section body"
                )
            if any(existing.name == ending_name for existing in endings):
                raise ValueError(f"duplicate section ending: {section_name!r}:{ending_name!r}")
            endings.append(SectionEnding(name=ending_name, rows=block.rows))
            continue

        if block.header.name in seen_names:
            raise ValueError(_duplicate_form_message(block.header.name))
        seen_names.add(block.header.name)
        forms.append(Form(name=block.header.name, items=parse_form_body_lines(block.body_lines)))

    return Document(
        meter=meter,
        metadata=metadata,
        sections=tuple(
            Section(
                name=section_name,
                body=section_bodies[section_name],
                endings=tuple(section_endings[section_name]),
            )
            for section_name in section_order
        ),
        forms=tuple(forms),
    )


def _match_section_header(text: str) -> SectionHeader | None:
    match = _SECTION_HEADER_RE.fullmatch(text)
    if match is None:
        return None
    return SectionHeader(name=match.group("name"), ending=match.group("ending"))


def _match_form_header(text: str) -> FormHeader | None:
    match = _FORM_HEADER_RE.fullmatch(text)
    if match is None:
        return None
    return FormHeader(name=match.group("name"))


def _decode_form_text_escape(source: str, index: int) -> tuple[str, int]:
    next_index = index + 1
    if next_index < len(source) and source[next_index] in "\\[]":
        return source[next_index], next_index + 1
    return "\\", next_index


def _parse_form_ref(text: str) -> FormSectionRef | None:
    match = _FORM_REF_RE.fullmatch(text)
    if match is None:
        return None
    return FormSectionRef(name=match.group("name"), ending=match.group("ending"))


def _duplicate_form_message(name: str | None) -> str:
    if name is None:
        return "duplicate plain form block"
    return f"duplicate named form block: {name!r}"
