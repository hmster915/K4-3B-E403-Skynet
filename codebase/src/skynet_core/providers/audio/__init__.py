"""
AudioProvider             --> STT provider contract
ElevenLabsAudioProvider   --> ElevenLabs realtime STT
TranscriptBuffer          --> gom transcript
"""

from .base import AudioProvider
from .buffer import TranscriptBuffer
from .elevenlabs import (
    ElevenLabsAudioProvider,
    RealtimeTranscriptionError,
)


__all__ = [
    "AudioProvider",
    "ElevenLabsAudioProvider",
    "TranscriptBuffer",
    "RealtimeTranscriptionError",
]