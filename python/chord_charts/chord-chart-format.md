# HIJ Chord Chart Format

Status: draft `v0.1`

This document describes a small text format for chord-grid lead sheets. The design target is a hand-edited, monospace-friendly chart format closer to an iReal-style roadmap than to ChordPro, while still being structured enough to parse, validate, linearize, and reformat.

## Goals

- Chord grids first; lyrics are optional overlays, not mixed into the grid.
- Shared section bodies plus explicit ending blocks.
- Deterministic parse/format normalization through an in-memory AST.
- Support for both `HIJKL` and conventional accidental note spellings on input.
- Clean autoformatting with stable beat-aligned chord durations.
- A data model that maps naturally to OCaml-style variants or frozen Python dataclasses.

## Non-goals for v0.1

- Melody notation.
- Rhythmic precision below one chord per beat.
- Syncopated hits or arbitrary offsets inside a beat.
- Advanced accidental spellings such as `Cb`, `B#`, `E#`, or double sharps/flats.
- Inferring section bodies/endings from fully linearized variants.

## Worked Example

```text
title: Just Friends
meter: 4/4

[A]:
| Hma#11 | -       | Hm      | B7      |
| K      | -       | Em      | A7      |
| Lm     | I7      | Chd F7  | Jm      |

[A:1]:
| L7     | -       | Lm      | I7  K7  |

[A:2]:
| Lm     | I7      | K       | Im  K7  |

form:
[A:1]
[A:2]

form[lyrics]:
[A:1]
just friends, lovers no more

[A:2]
just friends, but not like before
```

Semantically:

- `A` has one shared body and two authored endings.
- `A:1` and `A:2` are derived full variants: `body(A) + ending(A:1)` and `body(A) + ending(A:2)`.
- `form:` gives the canonical play order.
- `form[lyrics]:` must refer to the same sequence of section variants, but may contain arbitrary text around those references.

## File Structure

The file has three parts, in order:

1. Header fields.
2. Section blocks.
3. Form blocks.

After the first `form` block appears, no more section blocks are allowed. This keeps the grammar simple and avoids ambiguity with bracketed section references inside form blocks.

### Header Fields

Header lines use `name: value` syntax and must appear before the first section block.

Recognized fields in `v0.1`:

- `title: ...`
- `meter: N/4` (optional; defaults to `4/4`)

Unknown headers are allowed and should be preserved as opaque metadata fields.

`meter` is global for the whole chart in `v0.1`. Only quarter-note beat meters are supported for now, such as `3/4`, `4/4`, and `5/4`.

If the `meter` header is omitted, the parser behaves as though `meter: 4/4` were present.

### Section Blocks

Section blocks define the harmonic material.

```text
[A]:
| ... |
| ... |

[A:1]:
| ... |
```

Rules:

- A section definition header is `[` `section-name` [`:` `ending-name`] `]:`.
- `[A]:` defines the body for section `A`.
- `[A:1]:` defines ending `1` for section `A`.
- The body is required before any endings for that section.
- A section may have zero or more endings.
- Each ending name must be unique within its section.

`section-name` and `ending-name` are identifiers matching:

```text
[A-Za-z0-9_-]+
```

This allows names such as `A`, `B`, `bridge`, `tag`, `1`, `2`, or `outro`.

### Form Blocks

Form blocks define traversal order and optional overlays.

```text
form:
[A:1]
[B]
[A:2]

form[lyrics]:
[A:1]
some raw text here
[B]
more raw text
[A:2]
```

Rules:

- A plain form block header is `form:`.
- A named form block header is `form[` `name` `]:`.
- Inside a form block, unescaped bracketed section references are parsed structurally.
- Within raw text, `\[` and `\]` mean literal brackets, and `\\` means a literal backslash.
- Raw text content is stored unescaped in memory. The parser decodes these escapes when constructing `FormItem.text`.
- When formatting back to source text, literal `\`, `[`, and `]` characters in form text must be re-escaped.
- Everything else inside a form block is raw text.

All form blocks must contain the same sequence of section references in the same order.

If a plain `form:` block exists, it is the canonical traversal order. If it does not exist, the first named form block establishes the traversal order.

## Section References and Variants

A section reference inside a form block is one of:

- `[A]`
- `[A:1]`
- `[bridge]`
- `[bridge:outro]`

Rules:

- `[A]` refers to the body-only variant of section `A`.
- `[A:1]` refers to the derived variant `body(A) + ending(A:1)`.
- If a section has one or more endings, plain `[A]` is invalid in `form` in `v0.1`.
- If a section has no endings, `[A]` is the only valid reference form.

## Bar Syntax

Section bodies and endings consist of bar rows.

```text
| H      | -       | I7+     | -       |
| Im     | K7      | H   Lm  | Im  K7  |
```

Each row is a sequence of bars delimited by `|`.

Rules:

- Leading indentation is ignored.
- Each non-empty row in a section block must contain at least one `|`.
- A bar cell is the text between two adjacent `|` characters.
- Blank cells are invalid. If the harmony should continue from the previous bar, write `-`.

## Chord Tokens

A bar cell contains one or more tokens separated by one or more ASCII spaces. Tokens are maximal non-space substrings. Each token is either:

- a chord symbol, or
- `-`, meaning “carry the previous harmony into this bar.”

Chord symbols are parsed as:

```text
root + suffix + optional("/" + bass)
```

Lexing rules:

- Parse the root as the longest valid note lexeme at the start of the token.
- If a slash chord is present, the final `/` in the token introduces the bass, and the bass is parsed as the longest valid note lexeme immediately following that `/`.
- Everything between the root and the optional terminal `/bass` is the opaque suffix.
- `/` is reserved for slash-bass notation in `v0.1` and is not otherwise part of the suffix syntax.

Examples:

- `C`
- `Bbmaj7`
- `B7b9`
- `G7Am` parses as one token with root `G` and suffix `7Am`; it is not split into two chords
- `Hm7`
- `J7#11`
- `G/B`
- `Im`
- `Ksus/L`

The parser treats the suffix as opaque text. `maj7`, `m7b5`, `hd`, `alt`, `sus`, `ma#11`, `7b9`, and similar extensions are not interpreted semantically in `v0.1`; they are preserved as written.

### Accepted Note Lexemes

The parser always accepts the mixed input vocabulary:

- `A B C D E F G H I J K L`
- `C# Db D# Eb F# Gb G# Ab A# Bb`

Note lexemes are case-sensitive.

The canonical pitch-class mapping is:

```text
C = 0
K / C# / Db = 1
D = 2
L / D# / Eb = 3
E = 4
F = 5
H / F# / Gb = 6
G = 7
I / G# / Ab = 8
A = 9
J / A# / Bb = 10
B = 11
```

Only the common single-accidental spellings above are supported in `v0.1`.

## Chord Duration Model

Chord duration is an integer number of beats. For `meter: N/4`, each bar spans exactly `N` beats.

Within a bar, each token marks a harmony onset. The token remains in effect until the next token onset or the end of the bar.

Examples in `4/4`:

```text
| Dm7             |
```

`Dm7` lasts 4 beats.

```text
| Dm7     G7      |
```

`Dm7` lasts 2 beats and `G7` lasts 2 beats.

```text
| -       G7      |
```

The previous harmony continues for 2 beats, then `G7` lasts 2 beats.

Examples in `3/4`:

```text
| Am      D7  |
```

`Am` lasts 2 beats and `D7` lasts 1 beat.

```text
| Am  D7      |
```

`Am` lasts 1 beat and `D7` lasts 2 beats.

### `-` Carry Token

`-` is only valid as the first token in a bar.

It means:

- there is no chord change at beat 1 of this bar;
- the previous harmony continues until the next token or bar end.

If a `-` bar is encountered before any previous harmony exists in linear playback order, that is a validation error.

Carry validation is checked after form linearization, not in isolation at section-parse time.

## Raw and Canonical Parsing Modes

The parser should support two input modes:

- `raw`
- `canonical`

This is a parser setting, not a file header.

### Canonical Mode

Canonical mode is what the autoformatter emits.

For a bar with `N` beats, let `W` be the width of the bar cell in characters. Canonical bars must satisfy:

- `W % N == 0`
- `slotWidth = W / N`
- every token starts exactly at a beat boundary column:
  `0, slotWidth, 2 * slotWidth, ..., (N - 1) * slotWidth`
- for any consecutive tokens with start columns `c_i < c_{i+1}` and rendered text lengths `len_i`, canonical text must satisfy:
  `len_i <= c_{i+1} - c_i - 1`

Beat numbers are then:

- column `0` -> beat `1`
- column `slotWidth` -> beat `2`
- ...
- column `(N - 1) * slotWidth` -> beat `N`

Token duration is derived from the next token start or the bar end.

This ensures that canonical text always leaves at least one ASCII space between consecutive tokens. The formatter must choose `slotWidth` large enough to satisfy that spacing rule.

For a token at beat `b_i` followed by a token at beat `b_{i+1}`, this means:

```text
len_i + 1 <= (b_{i+1} - b_i) * slotWidth
```

For the final token in a bar at beat `b_k`, the rendered token must fit before the bar end:

```text
len_k <= (N - b_k + 1) * slotWidth
```

The formatter may choose any `slotWidth >= 1` that satisfies these constraints. In practice it will usually choose a common `slotWidth` across a row or across the whole chart for neat alignment.

### Raw Mode

Raw mode accepts uneven spacing and infers beat onsets deterministically.

Algorithm:

1. Let the bar cell be the exact substring between the surrounding `|` delimiters.
2. Tabs are invalid. Within bar cells, only ASCII space `U+0020` is treated as whitespace.
3. Split the cell into maximal non-space tokens, and record each token's 0-based start column relative to the start of the cell.
4. Let `N` be the meter numerator, `W` the cell width in characters, and `k` the number of tokens.
5. Reject the cell if `k == 0` or `k > N`.
6. Reject the cell if any token other than the first is `-`.
7. Let `x_i` be the start column of token `i`, and define the ideal beat-start column for beat `b` as:

   ```text
   p(b) = ((b - 1) * W) / N
   ```

8. Choose a strictly increasing beat sequence `b_1, ..., b_k` such that:

   ```text
   b_1 = 1
   1 <= b_1 < b_2 < ... < b_k <= N
   ```

9. Among all valid beat sequences, choose one minimizing:

   ```text
   sum over i of (x_i - p(b_i))^2
   ```

10. If multiple beat sequences have the same minimum cost, choose the lexicographically earliest one.
11. Derive each token's duration in beats from the next assigned beat start, or from the bar end for the final token.

Raw mode is intentionally permissive. The intended workflow is:

1. parse raw text
2. validate
3. autoformat to canonical text
4. treat the canonical form as the stable representation

## Formatting Rules

Formatting is semantic, not byte-for-byte preserving. The original input text is not expected to round-trip exactly.

Instead, formatting defines a canonicalized text form. For any accepted input `original`, let:

```text
a = format(parse(original))
b = format(parse(a))
```

Then the required invariant is:

```text
a == b
```

In other words, one parse-and-format pass may normalize the source text, but the result must be a fixed point for subsequent parse-and-format passes using the same formatter settings.

Recommended formatter behavior:

- emit headers in a stable order, with unknown metadata preserved afterward;
- emit the effective `meter` explicitly, even when it was defaulted on input;
- group a section body with its endings;
- emit canonical bar spacing;
- align bars in a monospace-friendly grid;
- preserve raw text content in `form[...]` blocks, re-escaping only what is required for literal `\`, `[`, and `]`, and normalize section reference spelling;
- preserve original root and bass spellings by default whenever the parsed AST still carries them.

Rendering note spellings is an output policy, not a file feature. Useful output modes:

- `preserve`
- `hij`
- `accidental(flat-heavy)`
- `accidental(sharp-heavy)`

The default formatting mode is `preserve`. In that mode, unchanged chords should reuse their parsed `rootLexeme` and `bassLexeme` values rather than being respelled.

Before key-aware heuristics exist, the default accidental policies are:

- `flat-heavy`
  Use `Db Eb F# Ab Bb`.
- `sharp-heavy`
  Use `C# D# F# G# Bb`.

`flat-heavy` is a sensible default for jazz-oriented accidental output:

```text
Db Eb F# Ab Bb
```

`sharp-heavy` keeps `Bb` but respells the others sharply:

```text
C# D# F# G# Bb
```

## Data Model

The semantic core should be language-neutral and functional-friendly. In Python, the natural implementation is `@dataclass(frozen=True, slots=True)` plus explicit union aliases. In OCaml, the same structure maps naturally to records plus algebraic data types.

Type sketch:

```ts
type TextRange = {
  startByte: int
  endByte: int
}

type PitchClass = int  // constrained to 0..11

type MetadataField = {
  name: string
  value: string
  span: TextRange
}

type Meter = {
  numerator: int
  denominator: 4
  span: TextRange  // source span, or a synthetic zero-width span if defaulted
}

type Chart = {
  metadata: MetadataField[]
  meter: Meter
  sections: Section[]
  forms: FormBlock[]
  span: TextRange
}

type Section = {
  name: string
  body: Bar[]
  endings: Ending[]
  span: TextRange
}

type Ending = {
  name: string
  bars: Bar[]
  span: TextRange
}

type Bar = {
  beats: int
  items: BarItem[]
  span: TextRange
}

type BarItem =
  | {
      tag: "carry"
      startBeat: int
      durationBeats: int
      span: TextRange
    }
  | {
      tag: "chord"
      chord: ChordSymbol
      startBeat: int
      durationBeats: int
      span: TextRange
    }

type ChordSymbol = {
  rootPc: PitchClass
  bassPc?: PitchClass
  suffix: string
  rootLexeme: string
  bassLexeme?: string
  span: TextRange
}

type FormBlock = {
  name?: string
  items: FormItem[]
  span: TextRange
}

type FormItem =
  | {
      tag: "text"
      text: string  // unescaped content
      span: TextRange
    }
  | {
      tag: "ref"
      section: string
      ending?: string
      span: TextRange
    }
```

### Derived Types

Variants are derived, not authored independently.

```ts
type VariantRef = {
  section: string
  ending?: string
}

type LinearBar = {
  play: VariantRef
  sourceSection: string
  sourcePart: "body" | "ending"
  sourceEnding?: string
  sourceBarIndex: int
  bar: ResolvedBar
}

type ResolvedBar = {
  beats: int
  spans: ResolvedChordSpan[]
}

type ResolvedChordSpan = {
  chord: ChordSymbol
  startBeat: int
  durationBeats: int
  span: TextRange
}
```

Linearization uses the canonical form sequence. A reference `[A:2]` expands to:

```text
body(A) followed by ending(A:2)
```

Each emitted `LinearBar` keeps provenance so later tooling can retain section awareness even after expansion.

## Source-Preservation Metadata

The parser should preserve enough source information to support good diagnostics and non-destructive formatting.

Required source-preserving fields:

- `TextRange` on every meaningful node
- `rootLexeme` and `bassLexeme` on each chord

`TextRange` is half-open and measured in UTF-8 byte offsets. Line and column information may be derived separately by the implementation when presenting diagnostics.

Preserving original note lexemes allows a formatter to reflow the chart without respelling unchanged chords.

## Validation Rules

At minimum, a validator should check:

- exactly one body exists for each section name;
- ending names are unique within each section;
- all form references resolve;
- sections with endings are referenced only as `[section:ending]`;
- sections without endings are referenced only as `[section]`;
- all form blocks have the same reference sequence;
- each bar item starts on an integer beat within `1..N`;
- bar items are strictly increasing and non-overlapping;
- bar item durations sum to the full bar length;
- `-` appears only as the first token in a bar;
- no unresolved carry occurs at the beginning of linear playback.

## Likely v0.2 Extensions

- Inferring `body + endings` from imported full variants.
- Per-section meter changes.
- Optional section-level labels such as `section-name: "Verse"`.
- Key-aware accidental rendering heuristics.
- More explicit import/export bridges to iReal, Impro-Visor, or MusicXML.
