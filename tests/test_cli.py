import math
import tempfile
import unittest
import wave
from pathlib import Path

from visualizer_tool.cli import generate_frames


def _create_test_wav(path: Path, duration_s: float = 0.5, sample_rate: int = 8000) -> None:
    total_samples = int(duration_s * sample_rate)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for n in range(total_samples):
            value = int(15000 * math.sin(2 * math.pi * 440 * n / sample_rate))
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


if __name__ == "__main__":
    unittest.main()
