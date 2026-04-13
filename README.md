# visualizer-tool

Minimal CLI for WAV → visualization video.

## MVP outcome

Given a `.wav` file, produce a playable `.mp4` visualization video with one
default visual style in one command.

## Requirements

- Python 3.10+
- `ffmpeg` available on `PATH`
- `libprojectM` shared library available on the system (hard requirement)

## Quickstart (clean machine path)

```bash
python -m visualizer_tool ./input.wav ./output.mp4
```

If successful, the CLI prints the generated frame count and output video path.

## CLI help

```bash
python -m visualizer_tool --help
```

Primary arguments:

- `audio_file` - input WAV path (MVP supports WAV only)
- `output_video` - output MP4 path

Optional flags:

- `--fps` (default: `30`)
- `--width` (default: `1280`)
- `--height` (default: `720`)
- `--max-frames` (render only first N frames, useful for testing)
- `--frames-dir` (store intermediate PNGs in a specific folder)
- `--keep-frames` (keep temporary frame files when not using `--frames-dir`)

## MVP acceptance criteria

- **Supported input**: WAV (`.wav`) only.
- **Output format**: H.264 MP4 (`.mp4`) via `ffmpeg`.
- **Max tested resolution/duration in automated tests**: small synthetic inputs
  (up to 80x60 and 6 frames) to validate end-to-end behavior quickly.
- **Basic performance target**: command completes without crashing and produces
  sequential frames + playable output video for short WAV files.
- **User success path**: one command (`python -m visualizer_tool in.wav out.mp4`)
  on a machine with Python + ffmpeg.

## Known limitations (MVP)

- WAV is the only supported input format.
- Single built-in visual style.
- No real-time mode.
- `libprojectM` must be installed and discoverable by dynamic linker lookup.

## Reproducible pre-release validation command

```bash
python -m unittest -v
```
