from __future__ import annotations

from hypothesis import strategies as st

from chord_charts.model import Bar, CarryItem, ChordItem, ChordSymbol
from chord_charts.notes import (
    ACCEPTED_INPUT_LEXEMES,
    NOTE_SPELLING_POLICIES,
    NoteSpellingPolicy,
    pitch_class_for_lexeme,
)


def accepted_note_lexemes() -> st.SearchStrategy[str]:
    return st.sampled_from(ACCEPTED_INPUT_LEXEMES)


def pitch_classes() -> st.SearchStrategy[int]:
    return st.integers(min_value=0, max_value=11)


def note_spelling_policies() -> st.SearchStrategy[NoteSpellingPolicy]:
    return st.sampled_from(NOTE_SPELLING_POLICIES)


@st.composite
def valid_bars(draw: st.DrawFn, *, min_beats: int = 1, max_beats: int = 8) -> Bar:
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

        lexeme = draw(accepted_note_lexemes())
        suffix = draw(st.sampled_from(("", "m", "7", "maj7", "sus")))
        items.append(
            ChordItem(
                chord=ChordSymbol(
                    root_pc=pitch_class_for_lexeme(lexeme),
                    suffix=suffix,
                    root_lexeme=lexeme,
                ),
                start_beat=start,
                duration_beats=duration,
            )
        )

    return Bar(beats=beats, items=tuple(items))
