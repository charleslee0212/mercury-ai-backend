import React, { useState, useEffect, useRef } from 'react';

const websocket = new WebSocket(
  //"wss://mercury.work.gd:8000/live-transcription"
  'wss://10.0.0.126:8000/v2/live-transcription'
);
websocket.onerror = (error) => {
  console.log('WebSocket Error:', error);
};

const App = () => {
  const [recorder, setRecorder] = useState();
  const [partial, setPartial] = useState('');
  const [final, setFinal] = useState([]);
  const [transcript, setTranscript] = useState('');
  const audioContext = useRef();

  useEffect(() => {
    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const type = data.type;

      console.log(data);

      switch (type) {
        case 'partial':
          setPartial(data.transcription);
          break;
        case 'final':
          setPartial('');
          setFinal((prev) => {
            const arr = [...prev];
            arr.push(data.transcription);
            return arr;
          });
          break;
        default:
          console.log('Unspecified Type!');
      }
    };
  }, []);

  useEffect(() => {
    const oldFinal = [...final];
    oldFinal.push(partial);
    setTranscript(oldFinal.join(' '));
  }, [final, partial]);

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
          // Send PCM data to the WebSockets
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
      <p>{transcript}</p>
    </div>
  );
};

export default App;
