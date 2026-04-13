# visualizer-tool

A small CLI wrapper around libprojectm-style visualization that accepts a WAV
audio file and renders sequential PNG frames that can be assembled into a
video.

## Usage

```bash
python -m visualizer_tool /path/to/audio.wav /path/to/output_frames
```

Optional flags:

- `--fps` (default: `30`)
- `--width` (default: `1280`)
- `--height` (default: `720`)
- `--prefix` (default: `frame_`)
- `--max-frames` (render only first N frames)
- `--require-libprojectm` (fail if the shared library is not available)
