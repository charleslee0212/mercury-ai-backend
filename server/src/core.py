from pydantic import BaseModel
from collections.abc import Iterable
from config import word_timestamp_error_margin
import faster_whisper.transcribe
import re


class Word(BaseModel):
    start: float
    end: float
    word: str
    probability: float

    @classmethod
    def flatten_segments(cls, segments: Iterable["Segment"]) -> list["Word"]:
        words: list["Word"] = []
        for segment in segments:
            assert segment is not None

            words.extend(segment.words)

        return words

    def offset(self, seconds: float):
        self.start += seconds
        self.end += seconds


class Segment(BaseModel):
    id: int
    seek: int
    start: float
    end: float
    text: str
    tokens: list[int]
    temperature: float
    avg_logprob: float
    compression_ratio: float
    no_speech_prob: float
    words: list[Word] | None

    @classmethod
    def translate(
        cls, segments: Iterable[faster_whisper.transcribe.Segment]
    ) -> Iterable["Segment"]:
        for segment in segments:
            yield cls(
                id=segment.id,
                seek=segment.seek,
                start=segment.start,
                end=segment.end,
                text=segment.text,
                tokens=segment.tokens,
                temperature=segment.temperature,
                avg_logprob=segment.avg_logprob,
                compression_ratio=segment.compression_ratio,
                no_speech_prob=segment.no_speech_prob,
                words=(
                    [
                        Word(
                            start=word.start,
                            end=word.end,
                            word=word.word,
                            probability=word.probability,
                        )
                        for word in segment.words
                    ]
                    if segment.words is not None
                    else None
                ),
            )


class Transcription:
    def __init__(self, words: list[Word] = []) -> None:
        self.words: list[Word] = []
        self.type: str = "none"
        self.extend(words)

    @property
    def text(self) -> str:
        return " ".join(word.word for word in self.words).strip()

    @property
    def start(self) -> float:
        return self.words[0].start if len(self.words) > 0 else 0.0

    @property
    def end(self) -> float:
        return self.words[-1].end if len(self.words) > 0 else 0.0

    @property
    def duration(self) -> float:
        return self.end - self.start

    def after(self, seconds: float) -> "Transcription":
        return Transcription(
            words=[word for word in self.words if word.start > seconds]
        )

    def before(self, seconds: float) -> "Transcription":
        return Transcription(words=[word for word in self.words if word.end <= seconds])

    def replace(self, words: list[Word]) -> None:
        self.words = words

    def extend(self, words: list[Word]) -> None:
        self._ensure_no_word_overlap(words)
        self.words.extend(words)

    def merge(self, words: list[Word]) -> None:
        if len(words):
            overlap_start = words[0].start
            print(f"Merge Start: {overlap_start}")
            print(f"Self: {self.words}")
            print(f"Incoming: {words}")
            self.replace(words=self.before(overlap_start).words)
            self.extend(words=words)

    def _ensure_no_word_overlap(self, words: list[Word]) -> None:
        if len(self.words) > 0 and len(words) > 0:
            if words[0].start + word_timestamp_error_margin <= self.words[-1].end:
                raise ValueError(
                    f"Words overlap: {self.words[-1]} and {words[0]}. Error margin: {word_timestamp_error_margin}"
                )
        for i in range(1, len(words)):
            if words[i].start + word_timestamp_error_margin <= words[i - 1].end:
                raise ValueError(
                    f"Words overlap: {words[i - 1]} and {words[i]}. All words: {words}"
                )

    def reset(self) -> None:
        self.replace(words=[])
        self.type = "none"

    def set_partial(self):
        self.type = "partial"

    def set_final(self):
        self.type = "final"


def is_eos(text: str) -> bool:
    if text.endswith("..."):
        return False
    return any(text.endswith(punctuation_symbol) for punctuation_symbol in ".?!")


def to_full_sentences(words: list[Word]) -> list[list[Word]]:
    sentences: list[list[Word]] = [[]]

    for word in words:
        sentences[-1].append(word)
        if is_eos(word.word):
            sentences.append([])
    if len(sentences[-1]) == 0 or not is_eos(sentences[-1][-1].word):
        sentences.pop()
    return sentences


def word_to_text(words: list[Word]) -> str:
    return "".join(word.word for word in words)


def canonicalize_word(text: str) -> str:
    text = text.lower()
    return re.sub(r"[^a-z]", "", text)


def common_prefix(a: list[Word], b: list[Word]) -> list[Word]:
    i = 0
    while (
        i < len(a)
        and i < len(b)
        and canonicalize_word(a[i].word) == canonicalize_word(b[i].word)
    ):
        i += 1
    return a[:i]


def segments_to_text(segments: Iterable[Segment]) -> str:
    return "".join(segment.text for segment in segments).strip()
