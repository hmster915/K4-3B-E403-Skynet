"""
send_chunk() --> gửi một audio chunk
commit()     --> chốt transcript hiện tại
events()     --> nhận transcript realtime
close()      --> đóng session
connect()    --> mở realtime STT session
"""

from typing import AsyncIterator, Protocol

from skynet_core.models.transcript import (
    RealtimeTranscriptEvent,
)


class RealtimeAudioSession(Protocol):

    # Preflight:
    # Role=send live audio
    # Input=PCM bytes
    # Output=provider message
    # Decision boundary=no transcription logic
    # Failure/Test=network/provider failure

    async def send_chunk(
        self,
        audio_chunk: bytes,
    ) -> None:
        ...

    # Preflight:
    # Role=finalize current transcript segment
    # Input=none
    # Output=commit request
    # Decision boundary=segment boundary only
    # Failure/Test=closed/provider failure

    async def commit(
        self,
    ) -> None:
        ...

    # Preflight:
    # Role=receive STT events
    # Input=provider messages
    # Output=normalized realtime events
    # Decision boundary=no meeting inference
    # Failure/Test=invalid/error event

    def events(
        self,
    ) -> AsyncIterator[RealtimeTranscriptEvent]:
        ...

    # Preflight:
    # Role=close transport
    # Input=none
    # Output=closed session
    # Decision boundary=cleanup only
    # Failure/Test=idempotent

    async def close(
        self,
    ) -> None:
        ...


class RealtimeAudioProvider(Protocol):

    # Preflight:
    # Role=create realtime STT session
    # Input=provider configuration
    # Output=RealtimeAudioSession
    # Decision boundary=connection only
    # Failure/Test=auth/network failure

    async def connect(
        self,
    ) -> RealtimeAudioSession:
        ...