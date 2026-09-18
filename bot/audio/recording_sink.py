import threading
import wave
from pathlib import Path

import discord
from discord.ext import voice_recv


class PerUserWaveSink(voice_recv.AudioSink):
    """
    Lưu audio PCM của mỗi Discord user thành một file WAV riêng.
    """

    CHANNELS = 2
    SAMPLE_WIDTH = 2
    SAMPLE_RATE = 48000

    def __init__(self, output_dir: Path):
        super().__init__()

        self.output_dir = output_dir
        self.output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        self._files = {}
        self._paths = {}
        self._user_names = {}

        self._lock = threading.RLock()
        self.closed = threading.Event()

    def wants_opus(self) -> bool:
        # False => voice_recv decode Opus thành PCM
        return False

    def _create_user_file(
        self,
        user: discord.Member | discord.User
    ):
        filename = f"{user.id}.wav"

        path = self.output_dir / filename

        wav_file = wave.open(
            str(path),
            "wb"
        )

        wav_file.setnchannels(
            self.CHANNELS
        )

        wav_file.setsampwidth(
            self.SAMPLE_WIDTH
        )

        wav_file.setframerate(
            self.SAMPLE_RATE
        )

        self._files[user.id] = wav_file
        self._paths[user.id] = path
        self._user_names[user.id] = user.display_name

        print(
            f"[RECORD] Created WAV for "
            f"{user.display_name}: {path}"
        )

        return wav_file

    def write(
        self,
        user,
        data: voice_recv.VoiceData
    ):
        if user is None:
            return

        if getattr(user, "bot", False):
            return

        if not data.pcm:
            return

        with self._lock:
            wav_file = self._files.get(
                user.id
            )

            if wav_file is None:
                wav_file = self._create_user_file(
                    user
                )

            wav_file.writeframes(
                data.pcm
            )

    def cleanup(self):
        with self._lock:
            for wav_file in self._files.values():
                try:
                    wav_file.close()
                except Exception as exc:
                    print(
                        "[RECORD] Error closing WAV:",
                        exc
                    )

            self._files.clear()

        self.closed.set()

        print("[RECORD] Audio sink cleaned up.")

    @property
    def audio_files(self):
        return dict(
            self._paths
        )

    @property
    def user_names(self):
        return dict(
            self._user_names
        )