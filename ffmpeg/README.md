# Using ffmpeg to rip audio from videos

I'm interested in this mainly as a catch-all way to get audio I can play on my
computer (e.g. a streaming service, including video formats) in a format that I
could run through transcription software.

The solution I've come up with so far is to use OBS to cast my computer session
to video and then extract audio.

OBS is GUI software and mostly a separate concern, but the key thing is that
once you have an OBS file, it's pretty easy to extract audio, e.g.
```
# lossless extraction
ffmpeg -i /path/to/recording.mkv  /path/to/audio.wav

# lossy extraction
ffmpeg -i /path/to/recording.mkv  /path/to/audio.mp3
```

The `ffmpeg` tool is extremely powerful and configurable with tons of flags,
but the vanilla default settings for these two formats seem to work well
enough for my purposes.

The default .mp3 file seems to be on the order of 10x smaller for a short
recording and it's possible that factor goes up with size depending on how the
compression works; in many cases it may not matter (or at any rate what really
matters is which format the transcription software I want to use prefers) but
this is good to know.
