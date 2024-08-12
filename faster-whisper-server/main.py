from fastapi import FastAPI, WebSocket, HTTPException, UploadFile, File
from faster_whisper import WhisperModel
from faster_whisper.vad import VadOptions, get_speech_timestamps
from io import BytesIO
import numpy as np
import uvicorn

app = FastAPI()

model_size = "large-v3"

# Run on GPU with FP16
# model = WhisperModel(model_size, device='cuda', compute_type='float16')

# or run on GPU with INT8
model = WhisperModel(model_size, device='cuda', compute_type='int8_float16')

# or run on CPU with INT8
# model = WhisperModel(model_size, device="cpu", compute_type="int8")

SAMPLES_PER_SECOND = 48000


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
    return int((duration * sample_rate) * (32//8))

def is_speaking(data):
    vad_options = VadOptions(min_silence_duration_ms=2000, speech_pad_ms=0)
    timestamps = get_speech_timestamps(data, vad_options)
    return len(timestamps) > 0


CHUNK_SIZE = get_chunk_size(1, 16000)
MAX_DURATION = get_chunk_size(10, 16000)

@app.websocket("/live-transcription")
async def transcribe(websocket: WebSocket):
    await websocket.accept()

    # Initialize variables for chunk-based processing
    buffer = BytesIO()

    # Keep track of processed chunks
    processed = 0

    while True:

        # Receive audio data in chunks
        data = await websocket.receive_bytes()

        buffer.seek(0, 2)
        buffer.write(data)
        buffer.seek(0)

        byte_data = buffer.getvalue()
        byte_len = len(byte_data)

        # Process complete chunks of audio data
        if byte_len // CHUNK_SIZE > processed:

            # VAD
            float_arry = np.frombuffer(byte_data[int(processed * CHUNK_SIZE):], dtype=np.float32)
            speaking = is_speaking(float_arry)
            if not speaking:
                processed += 1
                continue

            # Convert the chunk to PCM if necessary
            pcm_data = np.frombuffer(byte_data, dtype=np.float32)

            # Transcribe the audio chunk
            segments, info = model.transcribe(pcm_data)

            # Reset buffer at MAX_DURATION
            finilize = False
            if byte_len > MAX_DURATION:
                buffer.seek(0)
                buffer.truncate(0)
                processed = 0
                finilize = True

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

            await websocket.send_json({"partition": partition, "transcription": " ".join(transcription), "type": "final" if finilize else "partial"})
            processed += 1

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
