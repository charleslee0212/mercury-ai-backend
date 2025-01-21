import asyncio
import numpy as np
from numpy.typing import NDArray
from collections.abc import AsyncGenerator
from config import SAMPLE_RATE
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
import logging

logger = logging.getLogger(__name__)


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

    @property
    def size(self) -> int:
        return len(self.data)

    def after(self, ts: float) -> "Audio":
        adjust = ts - self.start if ts > self.duration else ts
        assert adjust <= self.duration
        return Audio(data=self.data[int(adjust * SAMPLE_RATE) :], start=ts)

    def extend(self, data: NDArray[np.float32]) -> None:
        self.data = np.append(self.data, data)

    def set(self, ts: float) -> None:
        assert ts <= self.duration
        self.data = np.array([self.data[int(ts * SAMPLE_RATE) :]], dtype=np.float32)
        self.start = 0.0

    def reset(self) -> None:
        self.data = np.array([], dtype=np.float32)
        self.start = 0.0


class AudioStream(Audio):
    def __init__(
        self,
        data: NDArray[np.float32] = np.array([], dtype=np.float32),
        start: float = 0.0,
    ) -> None:
        super().__init__(data=data, start=start)

        self.closed = False
        self.event = asyncio.Event()

    def extend(self, data: NDArray[np.float32]) -> None:
        assert not self.closed
        super().extend(data=data)
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
    try:
        while True:
            try:
                data = await websocket.receive_bytes()
            except RuntimeError as e:
                if 'WebSocket is not connected. Need to call "accept" first.' in str(e):
                    logger.error("WebSocket was disconnected! Exiting stream audio...")
                    break
                else:
                    raise

            float_array = np.frombuffer(data, dtype=np.float32)
            audio_stream.extend(float_array)

    except TimeoutError:
        logger.info("Timeout! No data was detected!")
    except WebSocketDisconnect as e:
        logger.info(f"Client disconnected: {e}")
