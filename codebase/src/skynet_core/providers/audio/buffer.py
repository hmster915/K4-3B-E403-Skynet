"""
__init__() --> tạo transcript buffer
add()      --> lưu committed text
build()    --> tạo full Transcript
is_empty() --> kiểm tra buffer rỗng
"""

from skynet_core.models.transcript import Transcript


class TranscriptBuffer:

    # Preflight: Role=create transcript buffer | Input=None | Output=empty buffer | Decision boundary=memory only | Failure/Test=starts empty
    def __init__(self) -> None:
        self._parts: list[str] = []

    # Preflight: Role=store committed STT | Input=text | Output=None | Decision boundary=no analysis | Failure/Test=ignore empty text
    def add(
        self,
        text: str,
    ) -> None:
        text = text.strip()

        if not text:
            return

        self._parts.append(text)

    # Preflight: Role=build final transcript | Input=stored text | Output=Transcript | Decision boundary=join only | Failure/Test=empty buffer error
    def build(self) -> Transcript:
        if self.is_empty():
            raise ValueError(
                "Transcript buffer is empty"
            )

        return Transcript(
            text="\n".join(self._parts)
        )

    # Preflight: Role=check buffer state | Input=None | Output=bool | Decision boundary=state only | Failure/Test=empty/non-empty
    def is_empty(self) -> bool:
        return not self._parts