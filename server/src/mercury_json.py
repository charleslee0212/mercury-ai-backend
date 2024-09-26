from pydantic import BaseModel
from faster_whisper.transcribe import TranscriptionInfo
from core import Transcription, Segment, Word, segments_to_text


class TranscriptionVerboseJsonResponse(BaseModel):
    task: str = "transcribe"
    language: str
    duration: float
    text: str
    words: list[Word]
    segments: list[Segment]

    @classmethod
    def from_segment(
        cls, segment: Segment, transcription_info: TranscriptionInfo
    ) -> "TranscriptionVerboseJsonResponse":
        return cls(
            language=transcription_info.language,
            duration=segment.end - segment.start,
            text=segment.text,
            words=(segment.words if isinstance(segment.words, list) else []),
            segments=[segment],
        )

    @classmethod
    def from_segments(
        cls, segments: list[Segment], transcription_info: TranscriptionInfo
    ) -> "TranscriptionVerboseJsonResponse":
        return cls(
            language=transcription_info.language,
            duration=transcription_info.duration,
            text=segments_to_text(segments),
            segments=segments,
            words=Word.from_segments(segments),
        )

    @classmethod
    def from_transcription(
        cls, transcription: Transcription
    ) -> "TranscriptionVerboseJsonResponse":
        return cls(
            language="english",  # FIX: hardcoded
            duration=transcription.duration,
            text=transcription.text,
            words=transcription.words,
            segments=[],  # FIX: hardcoded
        )
