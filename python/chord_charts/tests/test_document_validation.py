from __future__ import annotations

from textwrap import dedent

import pytest

import chord_charts
from chord_charts import (
    Document,
    DocumentValidationCode,
    DocumentValidationIssue,
    TextRange,
    assert_valid_document,
    parse_document,
    validate_document,
)


def _parse(text: str) -> Document:
    return parse_document(dedent(text).strip())


def _issue(code: DocumentValidationCode, message: str) -> DocumentValidationIssue:
    return DocumentValidationIssue(code=code, message=message, span=TextRange.synthetic())


def test_validate_document_accepts_matching_form_blocks_ignoring_text() -> None:
    document = _parse(
        """
        [A]:
        |C   |
        [A:1]:
        |G7  |
        [B]:
        |F   |
        form:
        [A:1]
        [B]
        form[lyrics]:
        intro [A:1]
        and [B]
        """
    )

    assert validate_document(document) == ()
    assert_valid_document(document)


@pytest.mark.parametrize(
    ("text", "expected_issue"),
    (
        (
            """
            [A]:
            |C   |
            form:
            [B]
            """,
            _issue("unknown_section", "form: references unknown section [B]"),
        ),
        (
            """
            [A]:
            |C   |
            [A:1]:
            |G7  |
            form:
            [A]
            """,
            _issue(
                "ending_required",
                "form: must reference section 'A' as [A:ending] because the section has endings",
            ),
        ),
        (
            """
            [A]:
            |C   |
            form:
            [A:1]
            """,
            _issue(
                "unexpected_ending",
                "form: must reference section 'A' as [A] because the section has no endings",
            ),
        ),
        (
            """
            [A]:
            |C   |
            [A:1]:
            |G7  |
            form:
            [A:2]
            """,
            _issue("unknown_ending", "form: references unknown ending [A:2]"),
        ),
    ),
)
def test_validate_document_reports_reference_semantic_issues(
    text: str, expected_issue: DocumentValidationIssue
) -> None:
    document = _parse(text)

    assert validate_document(document) == (expected_issue,)


def test_validate_document_reports_reference_issues_from_multiple_forms() -> None:
    document = _parse(
        """
        [A]:
        |C   |
        form:
        [B]
        form[alt]:
        [C]
        """
    )

    assert validate_document(document) == (
        _issue("unknown_section", "form: references unknown section [B]"),
        _issue("unknown_section", "form[alt]: references unknown section [C]"),
    )


def test_validate_document_skips_form_sequence_mismatch_when_canonical_form_is_invalid() -> None:
    document = _parse(
        """
        [A]:
        |C   |
        form:
        [B]
        form[lyrics]:
        [A]
        """
    )

    assert validate_document(document) == (
        _issue("unknown_section", "form: references unknown section [B]"),
    )


def test_validate_document_skips_form_sequence_mismatch_when_form_has_reference_issues() -> None:
    document = _parse(
        """
        [A]:
        |C   |
        [A:1]:
        |G7  |
        form:
        [A:1]
        form[lyrics]:
        [A]
        """
    )

    assert validate_document(document) == (
        _issue(
            "ending_required",
            "form[lyrics]: must reference section 'A' as [A:ending] because the section has endings",
        ),
    )


def test_validate_document_reports_form_sequence_mismatch_against_plain_form() -> None:
    document = _parse(
        """
        [A]:
        |C   |
        [B]:
        |F   |
        form:
        [A]
        [B]
        form[lyrics]:
        [B]
        [A]
        """
    )

    assert validate_document(document) == (
        _issue(
            "form_sequence_mismatch",
            "form[lyrics]: must match the canonical reference sequence [A] [B]; got [B] [A]",
        ),
    )


def test_validate_document_reports_unresolved_initial_carry_in_canonical_form() -> None:
    document = _parse(
        """
        [A]:
        |-   G7  |
        form:
        [A]
        """
    )

    assert validate_document(document) == (
        _issue(
            "unresolved_initial_carry",
            "canonical form begins with a carry before any harmony has been established",
        ),
    )


def test_validate_document_allows_carry_after_earlier_linearized_bar_establishes_harmony() -> None:
    document = _parse(
        """
        [A]:
        |C   |
        [A:1]:
        |-   |
        form:
        [A:1]
        """
    )

    assert validate_document(document) == ()
    assert_valid_document(document)


def test_validate_document_reports_unresolved_initial_carry_even_when_noncanonical_form_is_invalid() -> None:
    document = _parse(
        """
        [A]:
        |-   G7  |
        form:
        [A]
        form[lyrics]:
        [A:1]
        """
    )

    assert validate_document(document) == (
        _issue(
            "unexpected_ending",
            "form[lyrics]: must reference section 'A' as [A] because the section has no endings",
        ),
        _issue(
            "unresolved_initial_carry",
            "canonical form begins with a carry before any harmony has been established",
        ),
    )


def test_validate_document_skips_unresolved_initial_carry_when_canonical_form_is_invalid() -> None:
    document = _parse(
        """
        [A]:
        |-   G7  |
        form:
        [A:1]
        """
    )

    assert validate_document(document) == (
        _issue(
            "unexpected_ending",
            "form: must reference section 'A' as [A] because the section has no endings",
        ),
    )


def test_assert_valid_document_raises_value_error_for_invalid_document() -> None:
    document = _parse(
        """
        [A]:
        |C   |
        form:
        [A:1]
        """
    )

    with pytest.raises(
        ValueError, match=r"form: must reference section 'A' as \[A\] because the section has no endings"
    ):
        assert_valid_document(document)


def test_document_validation_api_is_exposed_from_package_root() -> None:
    assert chord_charts.validate_document is validate_document
    assert chord_charts.assert_valid_document is assert_valid_document
