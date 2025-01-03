from pydantic import BaseModel
from core import Transcription, Word


class MercuryTranscriptionJSON(BaseModel):
    text: str
    words: list[Word]
    duration: float
    type: str

    @classmethod
    def from_transcription(
        cls, transcription: Transcription
    ) -> "MercuryTranscriptionJSON":
        return cls(
            text=transcription.text,
            words=transcription.words,
            duration=transcription.duration,
            type=transcription.type,
        )
