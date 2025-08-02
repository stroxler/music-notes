# Ideas for what to build

## Programmable metronome

The single simplest tool that I'd like to build is a programmable
metronome that's a lot more powerful than most off-the-shelf ones.

I'm particularly interested in the ability to programmatically
play with two different kinds of clicks and set them somewhat
independently, which would be useful for many kinds of exercises,
for example:
- put a click every several bars (2, 4, or 8 are obvious options)
  and also a click on 2 and 4, but then have the more regular
  click drop out for stretches. This would help me judge how
  well I can keep time once it's been set; it's hard to use a
  single metronome for this because getting the rhythm locked
  in in the first place is so hard that you wind up testing that
  rather than your ability to keep it going.
- The guitarist Romain Pillon recommends putting your main click
  every 3 or 5 beats when playing in 4. This is a great idea, but
  it's easy to lose track of where you are, and the metronome
  doesn't give you feedback. If you had a different click on 1
  every 8 bars, you'd know whether you've gotten off track
- put a click every section end in a song form, which would help
  me test how well I'm keeping the form; a metronome alone doesn't
  do this very well because if you add or drop a bar, it won't
  tell you. This is something I especially need when practicing
  things that can cause me to lose my place:
  - weird time signatures... I lost the form playing some tunes in 7
  - practicing playing across the bar
  - trying to superimpose a different time signature on top of
    4/4 (this is something Eric Peralta recommends, especially
    3, 5, 6, 7, and 8... 8 is double-time feel, that's a good
    stopping point). This is useful in many contexts, but probably
    especially on bass - if you do it for a whole chunk of a tune
    it's an effect, but you could also do it for just a bar or
    two and it's a kind of drop; I think it's especially common
    to add some motion while playing in a very loose 2-feel.
- in settings where I can lose which *section* of the form I'm
  on, adding a double click or a third kind of click could help.
  I'm mainly thinking of rhythm changes right now, at the moment
  especially on bass I have to focus so hard to keep up that it's
  easy to lose track of which 'A' I am on

Doing this in Python makes perfect sense, although I think
it may turn out to be reasonable to try using Tidal Cycles instead
and just write a little tutorial on how to do that.

If that works, Tidal Cycles could also be used to start adding
pitched cues as well, for example playing a root on 1 at which point
you'd get the benefits of both a metronome and a gut check on things
like intonation.

## Ear trainer

A primary goal for a long time has been to start building
some ear training software. I've got a few pretty simple
approaches I want to explore, and it could get more complex
from there:

- First off, just setting a pitch center and playing a single
  note seems like one of the most valuable things. Much more
  than intervals, I think this sense of relative pitch is key.
  - Extending ^^ to short phrases of 2, 3, 4 notes is a logical
    next step
- Tracking chord movements - in particular setting a clear
  tonal center and then playing a progression either within
  that center or (especially) one that modulates.
  - Note that there are far fewer common modulations than there are
    melodic concepts, so even though this is really hard for me
    it's a limited vocabulary, and the software could basically just
    pull from a library of progressionsand generate some voicings.
  - This is probably the single most important ear skill for several things:
    - picking up new tunes by ear, including in real-time when needed
    - tracking what happens if the band decides to play altered changes
    - being able to listen and get back on track if you lose the form
    - improving my ability to memorize the changes of tunes by ear
      rather than by rote, and relate them to the melody
- Tracking modulations and and a few other things - especially identifying
  when the altered scale or a blues scale is being used - in a melody
  - In particular, I want to be able to hear this kind of information
    in a very fast-moving melody, even when I can't really track all the
    individual notes.
  - I'm guessing a library of licks is the most obvious way to get started
    with the ear trainer for this, although actually generating scale runs
    is potentially an option too; that might not sound musical though.
- More generally just building a library of licks and phrases I should
  be able to recognize within the context of a tonal center:
  - Pretty much any lick or snippet of a transcription can go here
  - Short snippets of song melodies are also great
  - Licks generated mechanically (e.g. broken arpeggios, pentatonic
    pattern runs, etc) could also be useful

More than the metronome, I'm pretty convinced that it's a good idea
to do this in Python, where I think the tools that come with music21 -
including the ability to parse and process an external pool of music
notation - will be incredibly valuable.

## Custom music markup language

I already started toying with this idea in `hij`, but basically
I'd like to come up with a notation - ideally a minor modification
of some existing notation - that lets me use the note names
H, I, J, K, and L for Gb, Ab, Bb, Db, and Eb.

That would be much more concise for music that involves a lot of
accidentals, and even for diatonic music it would significantly
simplify representation because the notation itself would not be
key-signature dependent.
