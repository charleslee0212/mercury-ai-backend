from audio import Audio, AudioStream
from mercury_asr import MercuryASR
from core import Transcription, Word, common_prefix, to_full_sentences, word_to_text
from config import CHUNK_DURATION
from vad import is_speaking
from collections.abc import AsyncGenerator


class LocalAgreement:
    def __init__(self) -> None:
        self.unconfirmed = Transcription()

    def merge(self, confirmed: Transcription, incoming: Transcription) -> list[Word]:
        incoming = incoming.after(confirmed.end - 0.1)
        prefix = common_prefix(incoming.words, self.unconfirmed.words)

        if len(incoming.words) > len(prefix):
            self.unconfirmed = Transcription(incoming.words[len(prefix) :])
        else:
            self.unconfirmed = Transcription()

        return prefix


def last_fs(confirmed: Transcription) -> float:
    full_sentences = to_full_sentences(confirmed.words)
    return full_sentences[-1][-1].end if len(full_sentences) > 0 else 0.0


def prompt(confirmed: Transcription) -> str | None:
    sentences = to_full_sentences(confirmed.words)
    return word_to_text(sentences[-1]) if len(sentences) > 0 else None


async def mercury_transcribe(
    audio_stream: AudioStream, mercury_asr: MercuryASR
) -> AsyncGenerator[Transcription, None]:
    full_audio = Audio()
    confirmed = Transcription()
    local_agreement = LocalAgreement()

    async for chunk in audio_stream.chunks(min_duration=CHUNK_DURATION):
        speaking = is_speaking(chunk)
        if not speaking:
            continue

        full_audio.extend(chunk)
        audio = full_audio.after(last_fs(confirmed=confirmed))

        transcription, _ = await mercury_asr.transcribe(
            audio=audio, prompt=prompt(confirmed=confirmed)
        )

        new_words = local_agreement.merge(confirmed=confirmed, incoming=transcription)

        if len(new_words) > 0:
            confirmed.extend(new_words)
            yield confirmed

    confirmed.extend(local_agreement.unconfirmed.words)
    yield confirmed
