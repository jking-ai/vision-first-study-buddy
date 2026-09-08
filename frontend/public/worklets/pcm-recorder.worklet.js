/**
 * AudioWorkletProcessor that captures raw microphone input and posts Float32Array chunks to the main thread.
 */
class PcmRecorderProcessor extends AudioWorkletProcessor {
  process(inputs, outputs, parameters) {
    const input = inputs[0];
    if (input && input.length > 0) {
      const channelData = input[0];
      if (channelData && channelData.length > 0) {
        // Clone the channel data buffer to post across threads
        this.port.postMessage(channelData.slice());
      }
    }
    return true;
  }
}

registerProcessor("pcm-recorder", PcmRecorderProcessor);
