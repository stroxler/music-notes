# How this project works


## The nix + pipenv environment

### Bootstrapping

To bootstrap the environment you need to manually run:
```
nix develop
pipenv install --dev
```
exactly once.

The very first time you do this in a new project you'll get a
`flake.lock` and a `Pipfile.lock`; if you do it on a new machine
with those locks in place you should get back the same environment.

### Developing

To manually enter a development shell, run
```
nix develop --command pipenv run $SHELL -l
```

If you have direnv installed it should work out of the box
with the provided .envrc:
```
use flake .
layout pipenv
```
This has the advantage of not starting a nested shell session.

## The provided tools

Musescore is available from nix as `mscore.`. By backing out the
directory, you can find the `.app` on MacOS which is important for some
of the music21 integrations to work.

Lilypond is available from nix on the path, although at the moment it
appears the music21 integration isn't working (lilypond complains about
a syntax error in the music21 output).

I didn't install `mingus` yet, at this point I'm not convinced it's
needed since music21 seems much more mature, but that could be worth
exploring someday.
