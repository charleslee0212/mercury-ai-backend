import asyncio
import numpy as np
from io import BytesIO
from numpy.typing import NDArray
from collections.abc import AsyncGenerator
from vad import is_speaking
from config import SAMPLE_RATE, CHUNK_DURATION
from fastapi import WebSocket, WebSocketDisconnect


class Audio:
    def __init__(
        self,
        data: NDArray[np.float32] = np.array([], dtype=np.float32),
        start: float = 0.0,
    ) -> None:
        self.data = data
        self.start = start

    @property
    def duration(self) -> float:
        return len(self.data) / SAMPLE_RATE

    @property
    def end(self) -> float:
        return self.start + self.duration

    def after(self, ts: float) -> "Audio":
        assert ts <= self.duration
        return Audio(data=self.data[int(ts * SAMPLE_RATE) :], start=ts)

    def extend(self, data: NDArray[np.float32]) -> None:
        self.data = np.append(self.data, data)

    def reset(self) -> None:
        self.data = np.array([], dtype=np.float32)
        self.start = 0.0


class AudioStream(Audio):
    def __init__(
        self,
        data: NDArray[np.float32] = np.array([], dtype=np.float32),
        start: float = 0.0,
    ) -> None:
        super.__init__(data, start)

        self.closed = False
        self.event = asyncio.Event()

    def extend(self, data: NDArray[np.float32]) -> None:
        assert not self.closed
        super().extend(data)
        self.event.set()

    def close(self) -> None:
        assert not self.closed
        self.closed = True
        self.event.set()

    def slice(self, ts: float) -> NDArray[np.float32]:
        return self.data[int(ts * SAMPLE_RATE) :]

    async def chunks(
        self, min_duration: float
    ) -> AsyncGenerator[NDArray[np.float32], None]:
        ts = 0.0
        while True:
            await self.event.wait()
            self.event.clear()

            # if the stream is closed, end generator
            # if there are remainding data, yeild rest of data
            if self.closed:
                if self.duration > ts:
                    yield self.slice(ts=ts)
                return

            # yield chunks of data by min_duration
            if self.duration - ts >= min_duration:
                ts_ = ts
                ts = self.duration
                yield self.slice(ts=ts_)


async def stream_audio(websocket: WebSocket, audio_stream: AudioStream) -> None:
    # Accumulate a chunk for VAD processing
    buffer = BytesIO()
    CHUNK_SIZE = int(CHUNK_DURATION * SAMPLE_RATE)
    try:
        while True:

            data = await websocket.receive_bytes()

            buffer.seek(0, 2)
            buffer.write(data)
            buffer.seek(0)

            byte_data = buffer.getvalue()
            byte_len = len(byte_data)

            if byte_len >= CHUNK_SIZE:

                # VAD
                float_arry = np.frombuffer(byte_data, dtype=np.float32)
                speaking = is_speaking(float_arry)
                buffer.seek(0)
                buffer.truncate(0)
                if not speaking:
                    continue

                chunk = np.frombuffer(byte_data, dtype=np.float32)

                audio_stream.extend(chunk)

    except TimeoutError:
        print("Timeout! No data was detected!")
    except WebSocketDisconnect as e:
        print(f"Client disconnected: {e}")
