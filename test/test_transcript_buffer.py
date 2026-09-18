from skynet_core.providers.audio.buffer import TranscriptBuffer


def test_buffer_builds_full_transcript() -> None:
    buffer = TranscriptBuffer()

    buffer.add("Khoa làm backend.")
    buffer.add("Chiến làm AI.")

    transcript = buffer.build()

    assert transcript.text == (
        "Khoa làm backend.\n"
        "Chiến làm AI."
    )


def test_buffer_ignores_empty_text() -> None:
    buffer = TranscriptBuffer()

    buffer.add("")

    assert buffer.is_empty()