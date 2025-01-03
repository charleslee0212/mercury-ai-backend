from fastapi import (
    FastAPI,
    WebSocket,
)
from fastapi.websockets import WebSocketState
from faster_whisper import WhisperModel
from mercury_asr import MercuryASR
from audio import AudioStream, stream_audio
from transcriber import mercury_transcribe, mercury_transcribe_v2
from logger_setup import set_up_logger
from mercury_json import MercuryTranscriptionJSON
import logging
import asyncio
from hypercorn.asyncio import serve
from hypercorn.config import Config

app = FastAPI()
set_up_logger()
logger = logging.getLogger(__name__)

model_size = "large-v3"

# Run on GPU with FP16
model = WhisperModel(model_size, device="cuda", compute_type="float16")

# or run on GPU with INT8
# model = WhisperModel(model_size, device="cuda", compute_type="int8_float16")

# or run on CPU with INT8
# model = WhisperModel(model_size, device="cpu", compute_type="int8")


@app.get("/")
def read_root():
    return {"hello": "world"}


@app.websocket("/v1/live-transcription")
async def transcribe(websocket: WebSocket):
    await websocket.accept()
    logger.info("Websocket connection accepted.")
    mercury_asr = MercuryASR(model)
    audio_stream = AudioStream()

    async with asyncio.TaskGroup() as tg:
        tg.create_task(stream_audio(websocket=websocket, audio_stream=audio_stream))
        async for transcript in mercury_transcribe(
            audio_stream=audio_stream, mercury_asr=mercury_asr
        ):
            logger.debug(f"Sending transcription: {transcript.text}")
            if websocket.client_state == WebSocketState.DISCONNECTED:
                break

            await websocket.send_json(
                MercuryTranscriptionJSON.from_transcription(transcript).model_dump()
            )

    if websocket.client_state != WebSocketState.DISCONNECTED:
        logger.info("Closing the connection.")
        websocket.close()


@app.websocket("/v2/live-transcription")
async def transcribe_v2(websocket: WebSocket):
    await websocket.accept()
    logger.info("Websocket connection accepted.")
    mercury_asr = MercuryASR(model)
    audio_stream = AudioStream()

    async with asyncio.TaskGroup() as tg:
        tg.create_task(stream_audio(websocket=websocket, audio_stream=audio_stream))
        async for transcript in mercury_transcribe_v2(
            audio_stream=audio_stream, mercury_asr=mercury_asr
        ):
            logger.debug(f"Sending transcription: {transcript.text}")
            if websocket.client_state == WebSocketState.DISCONNECTED:
                break

            await websocket.send_json(
                MercuryTranscriptionJSON.from_transcription(transcript).model_dump()
            )

    if websocket.client_state != WebSocketState.DISCONNECTED:
        logger.info("Closing the connection.")
        websocket.close()


if __name__ == "__main__":
    config = Config()
    config.bind = ["[::]:8000"]
    asyncio.run(serve(app, config))
