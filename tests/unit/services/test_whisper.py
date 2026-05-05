"""Tests unitaires pour la transcription Whisper."""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

from robot_hotel.services.whisper import transcribe_audio


class DummySegment:
    def __init__(self, text):
        self.text = text


class DummyModel:
    def __init__(self):
        self.calls = []

    def transcribe(self, audio_path, **kwargs):
        self.calls.append((audio_path, kwargs))
        return [DummySegment("bonjour"), DummySegment("je suis la")], SimpleNamespace(language="fr")


def test_transcribe_audio_forces_french_language(tmp_path):
    audio_file = tmp_path / "sample.wav"
    audio_file.write_bytes(b"fake wav data")

    model = DummyModel()
    result = transcribe_audio(model, str(audio_file))

    assert result["text"] == "bonjour je suis la"
    assert result["language"] == "fr"
    assert model.calls
    _, kwargs = model.calls[0]
    assert kwargs["language"] == "fr"
    assert kwargs["beam_size"] == 1
    assert kwargs["vad_filter"] is True
    assert kwargs["condition_on_previous_text"] is False