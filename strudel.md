# Using Strudel as a practice tool


My favorite potential tech tools to explore for building complex tools for
music practice right now are:
- Python, most likely music21, for complex music analysis
- TidalCycles - which I think is the most widely used live programming tool -
  for anything that's amenable to its pattern-based language


With that in mind, for really lightweight pattern-based stuff it seems like
[Strudel](https://strudel.cc), which is a js port of TidalCycles that runs in
the browser, is a great tool.

I'd rather use Tidal as a way to practice Haskell now and then if I'm doing
really cool stuff, but a lot of what I imagine doing with Tidal is really just
programmable metronome type stuff and can be done entirely in the pattern
language. And the ability to run it in the browser is a really big deal, because
I can use it anywhere without a whole dev setup phase.

# A first test: a Rhythm Changes metronome

I have a tendency to get lost on rhythm changes, particularly on bass because
just getting through the changes forces me to focus most of my mind on
measure-by-measure concerns so I lose the form.

Practicing with a metronome doesn't help much because I'm not getting lost
in a measure, I'm losing the form; in addition, since I want to really stress
test my ability to keep time I don't really want frequent clicks.

So let's build a custom practice track that gives us time + the form by putting
a sawtooth "click" that also tells us where we are in the harmony. We can also
vary a lowpass filter for some variety; not sure that adds much but it lets us
demo the use of effects:
```
const tempo = 200
const time_sig = 4
const measures_per_pattern = 2
setcpm(tempo / (time_sig * measures_per_pattern))
note("[<bb1 bb1 f2 bb1 bb1 bb1 f2 bb1 d2 g2 c2 f2> -] - - - - - - -")
.s("sawtooth").lpf("<600 400 500 400>")
```

# Another demo: using `sequence`

It's a little hard to see how to abstract the code above. That's okay,
it's doable to just write the pattern language for a given exercise
manually, but it might be nice to be able to write tools that make it
less fiddly.

I'm not sure how to produce the `<...>` behavior in plain code, but a
basic pattern can be written as `sequence` - here's a demo with a blues
bassline (in a '1' feel):
```
const tempo = 200
const time_sig = 4
const measures_per_pattern = 12
setcpm(tempo / (time_sig * measures_per_pattern))
sequence(
"bb1", "eb2", "bb1", "bb1",
"eb2", "eb2", "bb1", "bb1",
"c2",  "f2",  "bb1", "f2",
)
.note().s("sawtooth").lpf("400")
```


Now, while I don't know how to get `<...>` behavior, I do know how to get
`[...]`: just use an array with `[...]` in the javascript. Let's try making a
few of the changes faster:
```
const tempo = 200
const time_sig = 4
const measures_per_pattern = 12
setcpm(tempo / (time_sig * measures_per_pattern))
sequence(
"bb1", "eb2", "bb1", "bb1",
"eb2", "eb2", "bb1", ["d2", "g1"],
"c2",  "f2",  ["bb1", "g1"], ["c2", "f2"],
)
.note().s("sawtooth").lpf("400")
```
