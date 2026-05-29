# app0: Browser Audio Prototypes

Early prototypes exploring browser-based audio for jazz practice tools.

## Files

- `shell-voicings-tonejs.html` — Uses Tone.js built-in synths (triangle,
  sawtooth, FM). Three sound options. Works but sounds synthetic.
- `shell-voicings-soundfont.html` — Uses smplr to load SoundFont samples
  (piano + acoustic bass) from CDN. Sounds significantly better. This is
  the approach to build on.
- `walking-blues.html` — 12-bar blues with walking bass (acoustic bass
  SoundFont) and Charleston-rhythm piano comp (voice-led shell voicings).
  Selectable key and tempo. Sounds pretty good — validates smplr for
  multi-instrument playback.
- `blues-with-melody.html` — Adds a melody voice on top of the walking
  blues. Switchable instrument (sax, trumpet, guitar, vibes, clarinet,
  flute). Two pre-composed blues lick patterns alternate across choruses.
  Used to evaluate SoundFont quality across instruments.
- `tech-stack-investigation.md` — Broad landscape survey of browser audio,
  notation display, Python-in-browser, and music21 rewrite feasibility.

## What we learned

- **smplr + SoundFonts** is the right audio stack. Piano sounds great,
  bass is usable. Loads GM instruments from gleitz CDN via esm.sh, no
  bundling needed. Works even from `file://`.
- **Tone.js** synths are fine for a metronome but too synthetic for
  pitched instruments. Not needed if using smplr.
- **Bass note duration matters.** The SoundFont acoustic bass has
  more sustain than a real pizzicato bass. Setting duration to ~55%
  of the beat gives a tighter, more realistic feel. Default (80%+)
  sounds too legato.
- **Melody instrument quality varies widely.** Tested tenor/alto sax,
  trumpet, guitar (clean + OD), vibes, clarinet, flute. Results:
  - **Vibes**: best of the bunch, sounds quite solid
  - **Clarinet**: decent
  - **Saxes**: okay, passable
  - **Trumpet, guitar, flute**: noticeable synth/sample artifacts
  - For ear training exercises that need to sound good, vibes is the
    safest choice. Piano also works well (already validated).
- Shell voicing math is simple: root in octave 2, guide tones (3rd + 7th)
  in octave 3. Type A = 3rd below 7th, Type B = 7th below 3rd. Alternate
  for smooth voice leading in ii-V-I.
- m7 and m7b5 have identical shell voicings (same 3rd and 7th).

## Architecture for future work

The soundfont version already separates bass from piano via `playVoicing()`,
making it easy to add more voices (melody, drums). The pattern is: load a
`Soundfont` per instrument, schedule notes with `instrument.start({ note,
velocity, time, duration })`.

For Python integration later: Python would generate event lists (pitch,
time, duration, instrument) and pass them to JS via the Pyodide bridge.
The JS side just schedules events — no music theory needed in JS.
