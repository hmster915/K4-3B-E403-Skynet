"""
send_chunk() --> gửi audio realtime
commit()     --> chốt đoạn transcript
events()     --> nhận transcript event
close()      --> đóng session
connect()    --> mở realtime STT
"""

from collections.abc import AsyncIterator
from typing import Protocol

from skynet_core.models.transcript import RealtimeTranscriptEvent


class RealtimeAudioSession(Protocol):

    # Preflight: Role=send live audio | Input=PCM bytes | Output=None | Decision boundary=transport only | Failure/Test=empty/closed session
    async def send_chunk(
        self,
        audio_chunk: bytes,
    ) -> None:
        ...

    # Preflight: Role=commit current speech | Input=None | Output=None | Decision boundary=segment only | Failure/Test=closed session
    async def commit(self) -> None:
        ...

    # Preflight: Role=receive STT events | Input=provider stream | Output=realtime events | Decision boundary=no meeting inference | Failure/Test=provider error
    def events(
        self,
    ) -> AsyncIterator[RealtimeTranscriptEvent]:
        ...

    # Preflight: Role=close STT session | Input=None | Output=None | Decision boundary=cleanup only | Failure/Test=idempotent
    async def close(self) -> None:
        ...


class RealtimeAudioProvider(Protocol):

    # Preflight: Role=open realtime STT | Input=config | Output=session | Decision boundary=connection only | Failure/Test=auth/network error
    async def connect(
        self,
    ) -> RealtimeAudioSession:
        ...