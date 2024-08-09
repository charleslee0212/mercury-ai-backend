class PCMProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.port.onmessage = (event) => {
      if (event.data && event.data.type === 'start') {
        this.isRecording = true;
      } else if (event.data && event.data.type === 'stop') {
        this.isRecording = false;
      }
    };
  }
  process(inputs, outputs, parameters) {
    if (!this.isRecording) {
      return true;
    }

    const input = inputs[0];
    if (input && input[0]) {
      const inputChannelData = input[0];
      // Send raw PCM data to the main thread
      this.port.postMessage(inputChannelData);
    }

    return true;
  }
}

registerProcessor('pcm-processor', PCMProcessor);
