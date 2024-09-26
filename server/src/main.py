from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    HTTPException,
    UploadFile,
    File,
)
from fastapi.websockets import WebSocketState
from faster_whisper import WhisperModel
from faster_whisper.vad import VadOptions, get_speech_timestamps
from mercury_asr import MercuryASR
from audio import AudioStream, stream_audio
from transcriber import mercury_transcribe
from io import BytesIO
import numpy as np
import asyncio
import uvicorn

app = FastAPI()

model_size = "distil-large-v3"

# Run on GPU with FP16
# model = WhisperModel(model_size, device='cuda', compute_type='float16')

# or run on GPU with INT8
model = WhisperModel(model_size, device="cuda", compute_type="int8_float16")

# or run on CPU with INT8
# model = WhisperModel(model_size, device="cpu", compute_type="int8")


@app.get("/")
def read_root():
    return {"hello": "world"}


@app.get("/test-whisper")
def read_test_whisper():

    segments, info = model.transcribe("./tests/audio_files/test_audio.wav")
    partition = []
    transcription = []

    for segment in segments:
        partition.append(
            {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.lstrip(),
                "info": {
                    "language": info.language,
                    "probability": info.language_probability,
                },
            }
        )
        transcription.append(segment.text.lstrip())

    return {"partition": partition, "transcription": " ".join(transcription)}


@app.post("/whisper-upload")
async def post_audio(file: UploadFile = File(...)):
    if file.content_type not in [
        "audio/mpeg",
        "audio/wav",
        "audio/x-wav",
        "audio/flac",
    ]:
        raise HTTPException(
            status_code=400, detail="Invalid file type. Only audio files are allowed."
        )

    segments, info = model.transcribe(file.file)
    partition = []
    transcription = []

    for segment in segments:
        partition.append(
            {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.lstrip(),
                "info": {
                    "language": info.language,
                    "probability": info.language_probability,
                },
            }
        )
        transcription.append(segment.text.lstrip())

    return {"partition": partition, "transcription": " ".join(transcription)}


def get_chunk_size(duration, sample_rate):
    # 32 bit depth
    return int((duration * sample_rate) * (32 // 8))


def is_speaking(data):
    vad_options = VadOptions(min_silence_duration_ms=2000, speech_pad_ms=0)
    timestamps = get_speech_timestamps(data, vad_options)
    return len(timestamps) > 0


CHUNK_SIZE = get_chunk_size(1, 16000)


# accumulates audio PCM data for processing
@app.websocket("/v1/live-transcription")
async def transcribe(websocket: WebSocket):
    await websocket.accept()

    # Initialize variables for chunk-based processing
    buffer = BytesIO()
    audio = BytesIO()

    # Keep track of processed chunks
    processed = 0

    try:
        while True:

            # Receive audio data in chunks
            data = await websocket.receive_bytes()

            buffer.seek(0, 2)
            buffer.write(data)
            buffer.seek(0)

            byte_data = buffer.getvalue()
            byte_len = len(byte_data)

            # Process complete chunks of audio data
            if byte_len >= CHUNK_SIZE:

                # VAD
                float_arry = np.frombuffer(byte_data, dtype=np.float32)
                speaking = is_speaking(float_arry)
                buffer.seek(0)
                buffer.truncate(0)
                finilize = False
                if not speaking:
                    if len(audio.getvalue()) > 0:
                        finilize = True
                    else:
                        continue

                audio.seek(0, 2)
                audio.write(byte_data)
                audio.seek(0)

                audio_data = audio.getvalue()
                audio_len = len(audio_data)

                if finilize:
                    audio.seek(0)
                    audio.truncate(0)
                    processed = 0

                if audio_len // CHUNK_SIZE > processed:
                    # Convert the chunk to PCM
                    pcm_data = np.frombuffer(audio_data, dtype=np.float32)

                    # Transcribe the audio chunk
                    segments, info = model.transcribe(audio=pcm_data)

                    # Send transcription results
                    partition = []
                    transcription = []

                    for segment in segments:
                        partition.append(
                            {
                                "start": segment.start,
                                "end": segment.end,
                                "text": segment.text.lstrip(),
                                "info": {
                                    "language": info.language,
                                    "probability": info.language_probability,
                                },
                            }
                        )
                        transcription.append(segment.text.lstrip())

                    await websocket.send_json(
                        {
                            "partition": partition,
                            "transcription": " ".join(transcription),
                            "type": "final" if finilize else "partial",
                        }
                    )
                    processed += 1
    except TimeoutError:
        print("Timeout! No data was detected!")
    except WebSocketDisconnect as e:
        print(f"Client disconnected: {e}")


@app.websocket("/v2/live-transcription")
async def transcribe(websocket: WebSocket):
    await websocket.accept()
    mercury_asr = MercuryASR(model)
    audio_stream = AudioStream()

    async with asyncio.TaskGroup() as tg:
        tg.create_task(stream_audio(websocket=websocket, audio_stream=audio_stream))
        async for transcript in mercury_transcribe(
            audio_stream=audio_stream, mercury_asr=mercury_asr
        ):
            if websocket.client_state == WebSocketState.DISCONNECTED:
                break

            await websocket.send_text(transcript.text)

    if websocket.client_state != WebSocketState.DISCONNECTED:
        websocket.close()


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        ssl_keyfile="./SSL/key.pem",
        ssl_certfile="./SSL/cert.pem",
    )
