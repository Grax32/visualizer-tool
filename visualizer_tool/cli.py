from __future__ import annotations

import argparse
import configparser
import ctypes
import ctypes.util
import math
import os
import shutil
import struct
import subprocess
import tempfile
import wave
import zlib
from pathlib import Path

LIBPROJECTM_CANDIDATES = ("projectM", "libprojectM", "projectM-4")
LIBPROJECTM_PATH_ENV = "VISUALIZER_TOOL_LIBPROJECTM_PATH"
LIBPROJECTM_CONFIG_FILES = ("visualizer_tool.ini", ".visualizer_tool.ini")


def _configured_libprojectm_path() -> str | None:
    env_path = os.environ.get(LIBPROJECTM_PATH_ENV)
    if env_path:
        return env_path

    parser = configparser.ConfigParser()
    candidate_files = [Path.cwd() / LIBPROJECTM_CONFIG_FILES[0], Path.home() / LIBPROJECTM_CONFIG_FILES[1]]
    existing_files = [str(path) for path in candidate_files if path.is_file()]
    if not existing_files:
        return None

    parser.read(existing_files)
    if parser.has_option("libprojectm", "path"):
        configured_path = parser.get("libprojectm", "path").strip()
        if configured_path:
            return configured_path
    return None


class LibProjectMWrapper:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self._lib = self._load_libprojectm()
        if self._lib is None:
            raise RuntimeError(
                "libprojectM shared library was not found. "
                "Install libprojectM and ensure the library path is discoverable "
                "by the dynamic linker (for example, via LD_LIBRARY_PATH on Linux, "
                "DYLD_LIBRARY_PATH on macOS, or PATH on Windows). "
                "You can also set VISUALIZER_TOOL_LIBPROJECTM_PATH or configure "
                "[libprojectm] path=... in visualizer_tool.ini."
            )

    @staticmethod
    def _load_libprojectm() -> ctypes.CDLL | None:
        configured_path = _configured_libprojectm_path()
        if configured_path:
            try:
                return ctypes.CDLL(configured_path)
            except OSError:
                pass
        for name in LIBPROJECTM_CANDIDATES:
            lib_path = ctypes.util.find_library(name)
            if lib_path:
                try:
                    return ctypes.CDLL(lib_path)
                except OSError:
                    continue
        return None

    def render_frame(self, audio_level: float, frame_index: int) -> bytes:
        width = self.width
        height = self.height
        rgb = bytearray(width * height * 3)
        level = max(0.0, min(audio_level, 1.0))
        bar_height = max(1, int(level * (height - 1)))
        base_phase = frame_index * 0.12
        for y in range(height):
            row = y * width * 3
            for x in range(width):
                idx = row + x * 3
                wave_v = 0.5 + 0.5 * math.sin((x / max(width, 1)) * 18.0 + base_phase)
                threshold = height - int(bar_height * wave_v)
                if y >= threshold:
                    rgb[idx] = int(80 + 175 * wave_v)
                    rgb[idx + 1] = int(120 + 120 * (1.0 - wave_v))
                    rgb[idx + 2] = int(200 + 40 * level)
                else:
                    bg = int(10 + (y / max(height - 1, 1)) * 35)
                    rgb[idx] = bg
                    rgb[idx + 1] = bg
                    rgb[idx + 2] = min(255, bg + 20)
        return bytes(rgb)


def _decode_sample(sample_bytes: bytes, sample_width: int) -> int:
    if sample_width == 1:
        return sample_bytes[0] - 128
    if sample_width == 2:
        return int.from_bytes(sample_bytes, "little", signed=True)
    if sample_width == 3:
        value = int.from_bytes(sample_bytes, "little", signed=False)
        if value & 0x800000:
            value -= 0x1000000
        return value
    if sample_width == 4:
        return int.from_bytes(sample_bytes, "little", signed=True)
    raise ValueError(f"unsupported WAV sample width: {sample_width}")


def _sample_max_value(sample_width: int) -> float:
    if sample_width == 1:
        return 128.0
    return float(1 << (sample_width * 8 - 1))


def _read_audio_levels(audio_path: Path, fps: int, max_frames: int | None = None) -> list[float]:
    if audio_path.suffix.lower() != ".wav":
        raise ValueError("only WAV audio files are currently supported")

    with wave.open(str(audio_path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        total_samples = wav_file.getnframes()
        if channels < 1:
            raise ValueError("invalid WAV channel count")
        if sample_rate <= 0:
            raise ValueError("invalid WAV sample rate")

        samples_per_frame = max(1, int(sample_rate / fps))
        frame_samples = 0
        rms_levels: list[float] = []
        sample_peak = _sample_max_value(sample_width)

        while frame_samples < total_samples:
            read_count = min(samples_per_frame, total_samples - frame_samples)
            chunk = wav_file.readframes(read_count)
            frame_samples += read_count

            per_sample_bytes = sample_width * channels
            if not chunk:
                break

            energy = 0.0
            decoded = 0
            for offset in range(0, len(chunk), per_sample_bytes):
                summed = 0.0
                for ch in range(channels):
                    start = offset + ch * sample_width
                    end = start + sample_width
                    if end > len(chunk):
                        continue
                    summed += _decode_sample(chunk[start:end], sample_width)
                mono_sample = summed / channels
                normalized = mono_sample / sample_peak
                energy += normalized * normalized
                decoded += 1

            if decoded == 0:
                rms_levels.append(0.0)
            else:
                rms_levels.append(min(1.0, math.sqrt(energy / decoded)))

            if max_frames is not None and len(rms_levels) >= max_frames:
                break

    return rms_levels


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    length = struct.pack(">I", len(data))
    crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
    return length + chunk_type + data + struct.pack(">I", crc)


def _write_png(path: Path, width: int, height: int, rgb: bytes) -> None:
    if len(rgb) != width * height * 3:
        raise ValueError("RGB data length does not match frame dimensions")

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    stride = width * 3
    filtered_rows = bytearray()
    for row_start in range(0, len(rgb), stride):
        filtered_rows.append(0)
        filtered_rows.extend(rgb[row_start : row_start + stride])
    idat = zlib.compress(bytes(filtered_rows), level=6)
    png = signature
    png += _png_chunk(b"IHDR", ihdr)
    png += _png_chunk(b"IDAT", idat)
    png += _png_chunk(b"IEND", b"")
    path.write_bytes(png)


def generate_frames(
    audio_path: Path,
    output_dir: Path,
    fps: int = 30,
    width: int = 1280,
    height: int = 720,
    prefix: str = "frame_",
    max_frames: int | None = None,
) -> int:
    if fps <= 0:
        raise ValueError("fps must be a positive integer")
    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive integers")
    if max_frames is not None and max_frames <= 0:
        raise ValueError("max_frames must be positive when provided")

    levels = _read_audio_levels(audio_path, fps=fps, max_frames=max_frames)
    output_dir.mkdir(parents=True, exist_ok=True)
    renderer = LibProjectMWrapper(width=width, height=height)

    for index, level in enumerate(levels):
        frame_name = f"{prefix}{index:06d}.png"
        frame_path = output_dir / frame_name
        rgb = renderer.render_frame(level, index)
        _write_png(frame_path, width=width, height=height, rgb=rgb)

    return len(levels)


def assemble_video(
    frames_dir: Path,
    output_video: Path,
    fps: int = 30,
    prefix: str = "frame_",
    cleanup_frames: bool = False,
) -> None:
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path is None:
        raise RuntimeError(
            "ffmpeg was not found on PATH. Install ffmpeg and re-run this command."
        )

    output_video.parent.mkdir(parents=True, exist_ok=True)
    frame_pattern = str(frames_dir / f"{prefix}%06d.png")
    cmd = [
        ffmpeg_path,
        "-y",
        "-framerate",
        str(fps),
        "-i",
        frame_pattern,
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        str(output_video),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        stderr = result.stderr.strip() or "unknown ffmpeg error"
        raise RuntimeError(f"ffmpeg failed while creating video: {stderr}")

    if cleanup_frames:
        for frame in frames_dir.glob(f"{prefix}*.png"):
            frame.unlink()
        frames_dir.rmdir()


def generate_visualization_video(
    audio_path: Path,
    output_video: Path,
    fps: int = 30,
    width: int = 1280,
    height: int = 720,
    prefix: str = "frame_",
    max_frames: int | None = None,
    keep_frames: bool = False,
    frames_dir: Path | None = None,
) -> int:
    if frames_dir is None:
        temp_dir = Path(
            tempfile.mkdtemp(prefix=f"{output_video.stem}_frames_", dir=str(output_video.parent or Path(".")))
        )
    else:
        temp_dir = frames_dir

    frame_count = generate_frames(
        audio_path=audio_path,
        output_dir=temp_dir,
        fps=fps,
        width=width,
        height=height,
        prefix=prefix,
        max_frames=max_frames,
    )
    if frame_count == 0:
        raise RuntimeError("No frames were generated from the input WAV file.")

    assemble_video(
        frames_dir=temp_dir,
        output_video=output_video,
        fps=fps,
        prefix=prefix,
        cleanup_frames=not keep_frames and frames_dir is None,
    )
    return frame_count


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a visualization MP4 video from a WAV file."
    )
    parser.add_argument("audio_file", type=Path, help="Path to input WAV audio file")
    parser.add_argument("output_video", type=Path, help="Path to output MP4 video file")
    parser.add_argument("--fps", type=int, default=30, help="Frames per second")
    parser.add_argument("--width", type=int, default=1280, help="Output frame width")
    parser.add_argument("--height", type=int, default=720, help="Output frame height")
    parser.add_argument("--prefix", type=str, default="frame_", help="Frame file prefix (advanced)")
    parser.add_argument("--max-frames", type=int, default=None, help="Optional cap on generated frame count")
    parser.add_argument(
        "--frames-dir",
        type=Path,
        default=None,
        help="Optional directory for intermediate PNG frames (defaults to temporary directory)",
    )
    parser.add_argument(
        "--keep-frames",
        action="store_true",
        help="Keep generated frame PNGs when a temporary frame directory is used",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        frame_count = generate_visualization_video(
            audio_path=args.audio_file,
            output_video=args.output_video,
            fps=args.fps,
            width=args.width,
            height=args.height,
            prefix=args.prefix,
            max_frames=args.max_frames,
            keep_frames=args.keep_frames,
            frames_dir=args.frames_dir,
        )
    except (ValueError, RuntimeError, wave.Error) as err:
        parser.exit(2, f"Error: {err}\n")

    print(f"Generated {frame_count} frame(s) and wrote video: {args.output_video}")
    return 0
