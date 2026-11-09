"""Audio → [{text, start, end}] with faster-whisper. The model loads once, on first use.

Audio is decoded with the ffmpeg binary (already required) instead of PyAV, so library version
mismatches between faster-whisper and av can't break transcription.
"""

import subprocess
import threading
from pathlib import Path
from typing import TypedDict

import numpy as np
from faster_whisper import WhisperModel

from app.config import get_settings
from app.ingest.prepare import PrepareError, ffmpeg_path

SAMPLE_RATE = 16000

_model: WhisperModel | None = None
_lock = threading.Lock()


class Segment(TypedDict):
    text: str
    start: float
    end: float


def _get_model() -> WhisperModel:
    global _model
    with _lock:
        if _model is None:
            _model = WhisperModel(get_settings().whisper_model, device="cpu", compute_type="int8")
        return _model


def decode_audio(audio_path: Path) -> np.ndarray:
    """Decode any audio file to mono 16 kHz float32 samples."""
    cmd = [ffmpeg_path(), "-loglevel", "error", "-i", str(audio_path), "-f", "f32le", "-ac", "1", "-ar", "16000", "-"]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, timeout=1800)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise PrepareError("This recording could not be decoded.") from exc
    return np.frombuffer(result.stdout, dtype=np.float32)


def transcribe(audio_path: Path) -> tuple[list[Segment], float]:
    """Return timestamped segments and the audio duration in seconds."""
    samples = decode_audio(audio_path)
    model = _get_model()
    segments, _info = model.transcribe(samples, vad_filter=True, beam_size=5)
    result: list[Segment] = []
    for seg in segments:
        text = seg.text.strip()
        if text:
            result.append({"text": text, "start": round(seg.start, 2), "end": round(seg.end, 2)})
    return result, len(samples) / SAMPLE_RATE
