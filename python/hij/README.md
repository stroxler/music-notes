# HIJ: my music notation helper

This project is intended to be an exploration into a custom music
notation format I can use to avoid accidentals - about 6 months
ago I started using the names H-L for accidental notes, and I'd
like to have a music notation that allows me to do this; I also
want to have autoformat to align bar lines, which is a constant
pain point for me using abc notation.

As of writing this README, all I have is the project setup, I
haven't done any actual work yet.

## Nix + uv Setup

This is a new project layout for me: I'm using nix to bootstrap
system libraries (I'm using a normal app install of musescore now,
so the only system library I'm currently relying on is `lilypond`)
and the `uv` python installer.

Python libraries will be handled by `uv`.

I'm unsure how well this approach would work for native Python
development, but in the music world usually Python-space tools just
shell out to system tools, and nix+uv works great for this.


