import React, { useState, useEffect, useRef } from 'react';
import {
  IconButton,
  InputLabel,
  MenuItem,
  FormControl,
  Select,
  Grid2,
  Chip,
  Box,
} from '@mui/material';
import MicIcon from '@mui/icons-material/Mic';
import MicOffIcon from '@mui/icons-material/MicOff';
import Transcription from './components/transcription';
import Translation from './components/translation';
import gptModels from './options/gptModels';
import { options, map } from './options/languages';
import './styles/app.css';

const websocket = new WebSocket(
  // "wss://mercury.work.gd:8000/v2/live-transcription"
  'wss://api.mercury-ai.io/v2/live-transcription'
);
websocket.onerror = (error) => {
  console.log('WebSocket Error:', error);
};

const App = () => {
  const [recorder, setRecorder] = useState();
  const [partial, setPartial] = useState('');
  const [final, setFinal] = useState([]);
  const [listening, setListening] = useState(false);
  const [gpt, setGpt] = useState(gptModels[0]);
  const [selectedLanguages, setLanguages] = useState([]);
  const audioContext = useRef();

  useEffect(() => {
    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const type = data.type;

      console.log(data);

      switch (type) {
        case 'partial':
          setPartial(data.text);
          break;
        case 'final':
          setPartial('');
          setFinal((prev) => {
            const arr = [...prev];
            arr.push(data.text);
            return arr;
          });
          break;
        default:
          console.log('Unspecified Type!');
      }
    };
  }, []);

  const onclickStart = async () => {
    setListening(true);
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
    setListening(false);
    if (recorder) {
      recorder.port.postMessage({ type: 'stop' });
      audioContext.current.close();
      setRecorder();
    }
  };

  const gptHandler = (event) => {
    const {
      target: { value },
    } = event;
    setGpt(value);
  };

  const languagesHandler = (event) => {
    const {
      target: { value },
    } = event;
    setLanguages(value);
  };

  return (
    <div className="mercury-container">
      <Grid2
        container
        className="mercury-header"
        spacing={1}
        sx={{ alignItems: 'flex-start' }}
      >
        <Grid2 size={{ xs: 4, md: 2 }}>
          <FormControl className="mercury-gpt-model" fullWidth>
            <InputLabel id="mercury-gpt-model">GPT Model</InputLabel>
            <Select
              labelId="mercury-gpt-model"
              id="mercury-gpt-model-select"
              value={gpt}
              label="GPT Model"
              onChange={gptHandler}
            >
              {gptModels.map((model) => (
                <MenuItem value={model} key={model}>
                  {model}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid2>
        <Grid2 size={{ xs: 8, md: 4 }}>
          <FormControl className="mercury-languages" fullWidth>
            <InputLabel id="mercury-languages">Languages</InputLabel>
            <Select
              labelId="mercury-languages"
              id="mercury-languages-select"
              multiple
              value={selectedLanguages}
              label="GPT Model"
              onChange={languagesHandler}
              renderValue={(selected) => (
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                  {selected.map((value) => (
                    <Chip key={value} label={map[value]} />
                  ))}
                </Box>
              )}
            >
              {options.map((language) => (
                <MenuItem value={language.value} key={language.value}>
                  {language.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid2>
      </Grid2>
      <Grid2
        container
        spacing={1}
        className="mercury-transcription-translation"
        alignItems="flex-start"
        height="100%"
        overflow="hidden"
        direction={{ xs: 'column', md: 'row' }}
        wrap="nowrap"
      >
        <Grid2 className="mercury-transcription" size={{ xs: 12, md: 6 }}>
          <div className="mic-button">
            {listening ? (
              <IconButton onClick={onclickStop}>
                <MicOffIcon />
              </IconButton>
            ) : (
              <IconButton
                disabled={!selectedLanguages.length}
                onClick={onclickStart}
              >
                <MicIcon />
              </IconButton>
            )}
          </div>
          <Transcription partial={partial} final={final} />
        </Grid2>
        <Grid2 className="mercury-translation" size={{ xs: 12, md: 6 }}>
          <Translation
            model={gpt}
            languages={selectedLanguages}
            partial={partial}
            final={final}
          />
        </Grid2>
      </Grid2>
      <div className="footer"></div>
    </div>
  );
};

export default App;
