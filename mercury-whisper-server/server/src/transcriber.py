from audio import Audio, AudioStream
from mercury_asr import MercuryASR
from core import Transcription, Word, common_prefix, to_full_sentences, word_to_text
from config import CHUNK_DURATION, MAX_SENTENCES, SAMPLE_RATE, MAX_SILENCE
from vad import is_speaking
from collections.abc import AsyncGenerator
import logging

logger = logging.getLogger(__name__)


class LocalAgreement:
    def __init__(self) -> None:
        self.unconfirmed = Transcription()

    def merge(self, confirmed: Transcription, incoming: Transcription) -> list[Word]:
        incoming = incoming.after(confirmed.end - 0.1)
        prefix = common_prefix(incoming.words, self.unconfirmed.words)
        logger.debug(f"Confirmed: {confirmed.text}")
        logger.debug(f"Unconfirmed: {self.unconfirmed.text}")
        logger.debug(f"Incoming: {incoming.text}")

        if len(incoming.words) > len(prefix):
            self.unconfirmed = Transcription(incoming.words[len(prefix) :])
        else:
            self.unconfirmed = Transcription()

        return prefix


def last_fs(confirmed: Transcription) -> float:
    full_sentences = to_full_sentences(confirmed.words)
    return full_sentences[-1][-1].end if len(full_sentences) > 0 else 0.0


def last_confirmed_fs(confirmed: Transcription) -> float:
    full_sentences = to_full_sentences(confirmed.words)
    return full_sentences[-2][-1].end if len(full_sentences) > 1 else 0.0


def number_of_fs(confirmed: Transcription) -> int:
    full_sentences = full_sentences = to_full_sentences(confirmed.words)
    return len(full_sentences)


def prompt(confirmed: Transcription) -> str | None:
    sentences = to_full_sentences(confirmed.words)
    return word_to_text(sentences[-1]) if len(sentences) > 0 else None


async def mercury_transcribe(
    audio_stream: AudioStream, mercury_asr: MercuryASR
) -> AsyncGenerator[Transcription, None]:
    buffer = Audio()
    confirmed = Transcription()
    local_agreement = LocalAgreement()
    spoken = False

    async for chunk in audio_stream.chunks(min_duration=CHUNK_DURATION):
        speaking = is_speaking(chunk)
        if not speaking:
            logger.debug("No speech detected.")
            if spoken:
                spoken = False
                buffer.reset()
                confirmed.extend(local_agreement.unconfirmed.words)
                confirmed.set_final()
                logger.debug(f"Finalized transcription: {confirmed.text}")
                logger.debug("Reseting buffer...")
                yield confirmed
                confirmed.reset()
            continue
        spoken = True

        buffer.extend(chunk)

        audio = buffer.after(last_fs(confirmed=confirmed))

        transcription, _ = await mercury_asr.transcribe(
            audio=audio, prompt=prompt(confirmed=confirmed)
        )

        print(transcription.words)

        new_words = local_agreement.merge(confirmed=confirmed, incoming=transcription)

        if len(new_words) > 0:
            confirmed.extend(new_words)
            confirmed.set_partial()
            yield confirmed

    confirmed.extend(local_agreement.unconfirmed.words)
    yield confirmed


async def mercury_transcribe_v2(
    audio_stream: AudioStream, mercury_asr: MercuryASR
) -> AsyncGenerator[Transcription, None]:
    buffer = Audio()
    confirmed = Transcription()
    spoken = False
    silence_dur = 0
    processed = 0

    async for chunk in audio_stream.chunks(min_duration=CHUNK_DURATION):
        speaking = is_speaking(chunk)
        if not speaking:
            logger.debug("No speech detected.")
            silence_dur += len(chunk) / SAMPLE_RATE
            if silence_dur >= MAX_SILENCE:
                logger.debug(
                    "Reached max silence duration. Ending websocket connection..."
                )
                yield None
            if spoken:
                buffer.extend(chunk)
                transcription, _ = await mercury_asr.transcribe(audio=buffer)
                spoken = False
                if processed:
                    logger.debug(
                        f"Merging transcription: {confirmed.text} <-> {transcription.text}"
                    )
                    confirmed.merge(transcription.words)
                else:
                    logger.debug(
                        f"Replacing transcription: {confirmed.text} -> {transcription.text}"
                    )
                    confirmed.replace(transcription.words)
                confirmed.set_final()
                logger.debug(f"Finalized transcription: {confirmed.text}")
                yield confirmed
                logger.debug("Reseting buffer...")
                processed = 0
                buffer.reset()
                confirmed.replace([])
            continue
        spoken = True
        silence_dur = 0

        buffer.extend(chunk)

        transcription, _ = await mercury_asr.transcribe(audio=buffer)

        full_sentences = number_of_fs(confirmed=transcription)
        seconds = last_confirmed_fs(confirmed=transcription)
        if processed:
            logger.debug(
                f"Merging transcription: {confirmed.text} <-> {transcription.text}"
            )
            confirmed.merge(transcription.words)
        else:
            logger.debug(
                f"Replacing transcription: {confirmed.text} -> {transcription.text}"
            )
            confirmed.replace(transcription.words)

        if full_sentences // MAX_SENTENCES > processed:
            buffer = buffer.after(ts=seconds)
            processed += 1

        confirmed.set_partial()
        logger.debug(f"Partial transcription: {confirmed.text}")
        yield confirmed
