# MVP Progress Code Review (2026-04-13)

## Verdict

The repository is **largely on track for the stated MVP**: it provides a one-command
CLI path from WAV input to MP4 output, validates key error cases, and has fast
end-to-end automated coverage. Remaining risks are mostly around real-runtime
validation on machines with actual `libprojectM` and `ffmpeg` binaries.

## Scope reviewed

- Product definition and acceptance criteria in `README.md`
- CLI behavior and pipeline implementation in `visualizer_tool/cli.py`
- MVP-focused test coverage in `tests/test_cli.py`

## MVP criteria check

### 1) Supported input: WAV only

**Status: ✅ Met**

- Input extension is validated and non-WAV input raises a clear error.
- Tests explicitly verify rejection of non-WAV files.

### 2) Output format: H.264 MP4 via ffmpeg

**Status: ✅ Met (implementation + mocked test)**

- Video assembly invokes `ffmpeg` with `-c:v libx264` and `-pix_fmt yuv420p`.
- Missing-ffmpeg behavior is handled with actionable runtime error.
- Current tests mock `ffmpeg` invocation; no real-binary integration test yet.

### 3) One-command user success path

**Status: ✅ Met**

- CLI entrypoint supports `python -m visualizer_tool in.wav out.mp4`.
- Success output prints frame count and resulting output path.

### 4) Default visual style

**Status: ✅ Met**

- Renderer currently exposes a single built-in style path via
  `LibProjectMWrapper.render_frame`.

### 5) Automated confidence at small sizes

**Status: ✅ Met**

- Tests cover sequential frame generation, stereo WAV handling, invalid WAV,
  missing ffmpeg, and a mocked end-to-end pipeline at small frame counts.

## Gaps / risks before calling MVP fully validated

1. **No true runtime integration against system `libprojectM`.**
   - Tests patch library loading and never exercise real dynamic linking.
2. **No true runtime integration against real `ffmpeg`.**
   - Pipeline success test stubs subprocess execution.
3. **WAV gate is extension-based.**
   - Content-level format detection is delegated to `wave` parsing, which is fine
     for MVP but could be hardened later.

## Recommended next steps (high impact, low effort)

1. Add one opt-in integration test/job that runs only when both
   `ffmpeg` and `libprojectM` are installed.
2. Add a short release checklist item to manually validate:
   `python -m visualizer_tool sample.wav output.mp4` on a clean machine.
3. Keep current fast unit tests as default, with integration checks gated.
