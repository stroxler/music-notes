"""
Some helpers I started working on for working with music21. These are
generally useful, but I'm freezing this code as it was used in the
notebook "Going through the Music21 Docs" to make sure I don't later
break that notebook by accident.

I'll make a copy to keep iterating on in the future.
"""
import subprocess
import copy
from typing import Self

from music21 import (
    environment,
    note,
    pitch,
    duration,
    stream,
    converter,
)


def initialize_music21():
    """
    Initialize the music21 environment.
    
    Currently this assumes a MacOS setup because it relies on figuring out where
    the MuseScore `.app` directory is; it may work in general on MacOS but I
    wrote it mainly to be suitable for a nix shell.
    """
    user_settings = environment.UserSettings()

    # Find musescore provided via nix flakes
    MUSESCORE_EXE = subprocess.check_output(["which", "mscore."]).strip().decode()
    MUSESCORE_DIR = MUSESCORE_EXE.removesuffix('/bin/mscore.')
    MUSESCORE_APP = MUSESCORE_DIR + "/Applications/mscore.app/"
    user_settings["musicxmlPath"] = MUSESCORE_APP
    user_settings["musescoreDirectPNGPath"] = MUSESCORE_EXE

    # Find lilypond provided via nix flakes
    LILYPOND_EXE = subprocess.check_output(["which", "lilypond"]).strip().decode()
    LILYPOND_VERSION = subprocess.check_output(["lilypond", "--version"]).strip().decode().split()[2]
    user_settings["lilypondPath"] = LILYPOND_EXE
    user_settings["lilypondVersion"] = LILYPOND_VERSION

    return dict(user_settings)


def pitch_(p: float | pitch.Pitch) -> pitch.Pitch:
    return p if isinstance(p, pitch.Pitch) else pitch.Pitch(p) 


def duration_(d: float | duration.Duration) -> duration.Duration:
    return d if isinstance(d, duration.Duration) else duration.Duration(d) 


class Note(note.Note):
    """
    A more functional version of note.Note, easier to map over.
    """
    def with_pitch(
        self,
        p:  str | pitch.Pitch,
        /,
    ) -> Self:
        new = copy.deepcopy(self)
        new.pitch = pitch_(p)
        return new

    def with_duration(
        self,
        new_duration: float | duration.Duration,
        /,
    ) -> Self:
        new = copy.deepcopy(self)
        new.duration = duration_(d)
        return new


def make_note(p: str | pitch.Pitch, d: float | duration.Duration) -> Note:
    return Note(pitch_(p), duration=duration_(d))


mn = make_note


class Rest(note.Rest):
    """
    A more functional version of note.Rest, easier to map over.
    """
    def with_duration(
        self,
        new_duration: float | duration.Duration,
        /,
    ) -> Self:
        new = copy.deepcopy(self)
        new.duration = duration_(d)
        return new


def make_rest(d: float | duration.Duration) -> Rest:
    return Rest(duration=duration_(d))


mr = make_rest


def convert_modified_tiny_notation(modified_tiny_notation: str) -> str:
    """
    A very dumb search-and-replace attempt to use more lilypondesqe
    indicators for low notes. Turns, e.g. `g-,,` into `GG-`
    """
    code = modified_tiny_notation
    # Note that since we're using dumb search and replace rather than
    # proper parsing, we have to count backward.
    for count in range(3, 0, -1):
        commas = "," * count
        for character in "abcdefg":
            new_character = character.upper() * count
            for modifier in ["", "-", "--", "#", "##"]:
                old = f"{character}{modifier}{commas}"
                new = f"{new_character}{modifier}"
                code = code.replace(old, new)
    return code


def parse_tn(
    code: str,
) -> stream.Part:
    return converter.parse(code, format="tinyNotation")


def parse_mtn(
    code: str,
    debug_converter: bool = False,
) -> stream.Part:
    tiny_notation = convert_modified_tiny_notation(code)
    if debug_converter:
        print(tiny_notation)
    return parse_tn(tiny_notation)


# TODO: learn abc notation, it's widely used.
def parse_abc(
    code: str,
) -> stream.Score:
    return converter.parse(code, format="abc")


# TODO: look into "humdrum" notation!