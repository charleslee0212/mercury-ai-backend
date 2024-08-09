import React, { useState, useEffect, useRef } from 'react';

const websocket = new WebSocket('ws://127.0.0.1:8000/live-transcription');
websocket.onmessage = (event) => {
  console.log('Transcription:', event.data);
};
websocket.onerror = (error) => {
  console.log('WebSocket Error:', error);
};

const App = () => {
  const [recorder, setRecorder] = useState();
  const audioContext = useRef();

  const onclickStart = async () => {
    try {
      audioContext.current = new AudioContext({ sampleRate: 16000 });
      await audioContext.current.audioWorklet.addModule('./processor.js');
      const workletNode = new AudioWorkletNode(
        audioContext.current,
        'pcm-processor'
      );

      workletNode.port.onmessage = (event) => {
        if (event.data instanceof Float32Array) {
          // Send PCM data to the WebSocket
          websocket.send(event.data);
        }
      };
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const sourceNode = audioContext.current.createMediaStreamSource(stream);
      sourceNode.connect(workletNode);
      workletNode.connect(audioContext.current.destination);

      workletNode.port.postMessage({ type: 'start' });
      setRecorder(workletNode);
    } catch (error) {
      console.error('Audio Worklet Error:', error);
    }
  };

  const onclickStop = () => {
    if (recorder) {
      recorder.port.postMessage({ type: 'stop' });
      audioContext.current.close();
      setRecorder();
    }
  };

  return (
    <div>
      <button onClick={onclickStart}>Start</button>
      <button onClick={onclickStop}>Stop</button>
    </div>
  );
};

export default App;
