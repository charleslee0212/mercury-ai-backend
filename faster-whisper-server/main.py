from fastapi import FastAPI, WebSocket, HTTPException, UploadFile, File
from faster_whisper import WhisperModel
import numpy as np
import uvicorn

app = FastAPI()

model_size = "large-v3"

# Run on GPU with FP16
# model = WhisperModel(model_size, device='cuda', compute_type='float16')

# or run on GPU with INT8
# model = WhisperModel(model_size, device='cuda', compute_type='int8_float16')
# or run on CPU with INT8

model = WhisperModel(model_size, device="cpu", compute_type="int8")

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


CHUNK_SIZE = 1280000  # Define your chunk size (in bytes)


@app.websocket("/live-transcription")
async def transcribe(websocket: WebSocket):
    await websocket.accept()

    # Initialize variables for chunk-based processing
    buffer = bytearray()

    try:
        while True:
            # Receive audio data in chunks
            data = await websocket.receive_bytes()
            buffer.extend(data)

            print(len(buffer))

            # Process complete chunks of audio data
            while len(buffer) >= CHUNK_SIZE:
                chunk = buffer[:CHUNK_SIZE]
                buffer = buffer[CHUNK_SIZE:]

                # Convert the chunk to PCM if necessary
                pcm_data = np.frombuffer(chunk, dtype=np.float32)

                # Transcribe the audio chunk
                segments, info = model.transcribe(pcm_data)

                # Send transcription results
                for segment in segments:
                    response = {
                        "start": segment.start,
                        "end": segment.end,
                        "text": segment.text.lstrip(),
                        "info": {
                            "language": info.language,
                            "probability": info.language_probability,
                        },
                    }
                    await websocket.send_json(response)

    except Exception as e:
        await websocket.close(code=4000)  # Close the connection on error
        print(f"Error: {e}")

    finally:
        await websocket.close()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
