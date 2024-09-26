import asyncio
from faster_whisper import transcribe
from core import Transcription, Segment, Word
from audio import Audio


class MercuryASR:
    def __init__(self, whisper: transcribe.WhisperModel) -> None:
        self.whisper = whisper

    def _transcribe(
        self, audio: Audio, prompt: str | None = None
    ) -> tuple[Transcription, transcribe.TranscriptionInfo]:
        segments, transcription_info = self.whisper.transcribe(
            audio.data,
            initial_prompt=prompt,
            condition_on_previous_text=False,
            word_timestamps=True,
        )
        segments = Segment.translate(segments=segments)
        words = Word.flatten_segments(segments=segments)

        for word in words:
            word.offset(audio.start)

        transcription = Transcription(words=words)

        return (transcription, transcription_info)

    async def transcribe(
        self, audio: Audio, prompt: str | None = None
    ) -> tuple[Transcription, transcribe.TranscriptionInfo]:
        return await asyncio.get_running_loop().run_in_executor(
            None, self._transcribe, audio, prompt
        )
