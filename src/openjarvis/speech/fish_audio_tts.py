"""Fish Audio text-to-speech backend.

Uses the Fish Audio REST API. Set FISH_API_KEY in the environment.
The configured voice ID is passed as Fish Audio's reference_id.
"""

from __future__ import annotations

import io
import os
import wave
from typing import List

import httpx

from openjarvis.core.registry import TTSRegistry
from openjarvis.speech.tts import TTSBackend, TTSResult

_FISH_AUDIO_URL = "https://api.fish.audio/v1/tts"
_DEFAULT_MODEL = "s2.1-pro-free"
_DEFAULT_VOICE_ID = "14129c3e320149449d6bada6862f7338"
_ALLOWED_FORMATS = {"wav", "mp3", "pcm", "opus"}


def _normalize_api_key(value: str) -> str:
    key = value.strip()
    if any(not 33 <= ord(char) <= 126 for char in key):
        raise ValueError("Fish Audio API key contains unsupported characters")
    return key


def _fish_audio_synthesize(
    api_key: str,
    text: str,
    voice_id: str,
    *,
    model: str,
    output_format: str,
    speed: float,
) -> bytes:
    """Call Fish Audio and return the generated audio bytes."""
    key = _normalize_api_key(api_key)
    if not key:
        raise RuntimeError("FISH_API_KEY not set")
    if not voice_id:
        raise ValueError("Fish Audio voice ID is not configured")

    try:
        response = httpx.post(
            _FISH_AUDIO_URL,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "model": model,
            },
            json={
                "text": text,
                "reference_id": voice_id,
                "format": output_format,
                "prosody": {"speed": max(0.5, min(2.0, speed))},
            },
            timeout=120.0,
        )
        response.raise_for_status()
        return response.content
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"Fish Audio request failed (HTTP {exc.response.status_code})"
        ) from None
    except Exception as exc:
        raise RuntimeError(
            f"Fish Audio request failed ({type(exc).__name__})"
        ) from None


@TTSRegistry.register("fish_audio")
class FishAudioTTSBackend(TTSBackend):
    """Fish Audio cloud TTS backend."""

    backend_id = "fish_audio"

    def __init__(
        self,
        *,
        api_key: str = "",
        model: str = "",
        voice_id: str = "",
    ) -> None:
        self._api_key = _normalize_api_key(
            api_key or os.environ.get("FISH_API_KEY", "")
        )
        self._model = model or os.environ.get("FISH_AUDIO_MODEL", _DEFAULT_MODEL)
        self._voice_id = (
            voice_id
            or os.environ.get("FISH_AUDIO_VOICE_ID", "")
            or _DEFAULT_VOICE_ID
        )

    def synthesize(
        self,
        text: str,
        *,
        voice_id: str = "",
        speed: float = 1.0,
        output_format: str = "mp3",
    ) -> TTSResult:
        if not self._api_key:
            raise RuntimeError("FISH_API_KEY not set")
        fmt = output_format.lower()
        if fmt not in _ALLOWED_FORMATS:
            fmt = "mp3"
        selected_voice = voice_id or self._voice_id
        audio = _fish_audio_synthesize(
            self._api_key,
            text,
            selected_voice,
            model=self._model,
            output_format=fmt,
            speed=speed,
        )

        sample_rate = 24000
        if fmt == "wav":
            try:
                with wave.open(io.BytesIO(audio), "rb") as wav_file:
                    sample_rate = wav_file.getframerate()
            except (wave.Error, EOFError):
                raise RuntimeError("Fish Audio returned an invalid WAV file") from None
        elif fmt == "mp3":
            sample_rate = 44100

        return TTSResult(
            audio=audio,
            format=fmt,
            voice_id=selected_voice,
            sample_rate=sample_rate,
            metadata={"backend": self.backend_id, "model": self._model},
        )

    def available_voices(self) -> List[str]:
        return [self._voice_id] if self._voice_id else []

    def health(self) -> bool:
        return bool(self._api_key and self._voice_id)


__all__ = ["FishAudioTTSBackend"]
