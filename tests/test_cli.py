import math
import tempfile
import unittest
import wave
from pathlib import Path

from visualizer_tool.cli import _decode_sample, generate_frames

AMPLITUDE = 15000
FREQUENCY_HZ = 440


def _create_test_wav(path: Path, duration_s: float = 0.5, sample_rate: int = 8000) -> None:
    total_samples = int(duration_s * sample_rate)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for n in range(total_samples):
            value = int(AMPLITUDE * math.sin(2 * math.pi * FREQUENCY_HZ * n / sample_rate))
            wav_file.writeframesraw(value.to_bytes(2, "little", signed=True))


class GenerateFramesTests(unittest.TestCase):
    def test_generates_sequential_png_frames(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            audio_path = tmp_path / "tone.wav"
            output_dir = tmp_path / "frames"
            _create_test_wav(audio_path)

            frame_count = generate_frames(
                audio_path=audio_path,
                output_dir=output_dir,
                fps=10,
                width=64,
                height=36,
                max_frames=5,
            )

            self.assertEqual(frame_count, 5)
            generated = sorted(output_dir.glob("frame_*.png"))
            self.assertEqual(len(generated), 5)
            self.assertEqual(generated[0].name, "frame_000000.png")
            self.assertEqual(generated[-1].name, "frame_000004.png")
            self.assertEqual(generated[0].read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

    def test_rejects_non_wav_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            bad_audio = tmp_path / "input.mp3"
            bad_audio.write_bytes(b"not a wav")
            output_dir = tmp_path / "frames"

            with self.assertRaises(ValueError):
                generate_frames(audio_path=bad_audio, output_dir=output_dir)

    def test_generates_frames_for_stereo_wav(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            audio_path = tmp_path / "stereo.wav"
            output_dir = tmp_path / "frames"
            with wave.open(str(audio_path), "wb") as wav_file:
                wav_file.setnchannels(2)
                wav_file.setsampwidth(2)
                wav_file.setframerate(8000)
                for n in range(4000):
                    left = int(12000 * math.sin(2 * math.pi * 220 * n / 8000))
                    right = int(6000 * math.sin(2 * math.pi * 440 * n / 8000))
                    wav_file.writeframesraw(left.to_bytes(2, "little", signed=True))
                    wav_file.writeframesraw(right.to_bytes(2, "little", signed=True))

            frame_count = generate_frames(
                audio_path=audio_path,
                output_dir=output_dir,
                fps=8,
                width=48,
                height=32,
                max_frames=4,
            )

            self.assertEqual(frame_count, 4)
            self.assertEqual(len(list(output_dir.glob("frame_*.png"))), 4)

    def test_decode_sample_supports_all_configured_widths(self) -> None:
        self.assertEqual(_decode_sample(bytes([255]), 1), 127)
        self.assertEqual(_decode_sample((1234).to_bytes(2, "little", signed=True), 2), 1234)
        self.assertEqual(_decode_sample(bytes([0x10, 0x27, 0x00]), 3), 10000)
        self.assertEqual(
            _decode_sample((1_000_000).to_bytes(4, "little", signed=True), 4),
            1_000_000,
        )


if __name__ == "__main__":
    unittest.main()
