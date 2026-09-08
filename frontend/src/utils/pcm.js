/**
 * Audio PCM conversion and downsampling utilities for Voice Mode.
 */

/**
 * Downsample audio buffer to 16 kHz using linear decimation / averaging.
 * @param {Float32Array} input - Input audio samples
 * @param {number} inputSampleRate - Sampling rate of input buffer
 * @returns {Float32Array} Downsampled audio samples at 16 kHz
 */
export function downsampleTo16k(input, inputSampleRate) {
  if (inputSampleRate === 16000) {
    return input;
  }
  const ratio = inputSampleRate / 16000;
  const newLength = Math.round(input.length / ratio);
  const result = new Float32Array(newLength);
  let offsetResult = 0;
  let offsetInput = 0;

  while (offsetResult < result.length) {
    const nextOffsetInput = Math.round((offsetResult + 1) * ratio);
    let accum = 0;
    let count = 0;
    for (let i = offsetInput; i < nextOffsetInput && i < input.length; i++) {
      accum += input[i];
      count++;
    }
    result[offsetResult] = count > 0 ? accum / count : 0;
    offsetResult++;
    offsetInput = nextOffsetInput;
  }

  return result;
}

/**
 * Convert Float32Array audio samples (-1.0 to 1.0) to 16-bit PCM little-endian ArrayBuffer.
 * @param {Float32Array} input - Floating point audio samples
 * @returns {ArrayBuffer} 16-bit PCM buffer
 */
export function floatTo16BitPCM(input) {
  const buffer = new ArrayBuffer(input.length * 2);
  const view = new DataView(buffer);
  for (let i = 0; i < input.length; i++) {
    const s = Math.max(-1, Math.min(1, input[i]));
    const intSample = s < 0 ? Math.round(s * 0x8000) : Math.round(s * 0x7fff);
    view.setInt16(i * 2, intSample, true);
  }
  return buffer;
}

/**
 * Convert 16-bit PCM little-endian ArrayBuffer to Float32Array for AudioBuffer playback.
 * @param {ArrayBuffer} arrayBuffer - 16-bit PCM buffer
 * @returns {Float32Array} Normalized audio samples (-1.0 to 1.0)
 */
export function int16ToFloat32(arrayBuffer) {
  const view = new DataView(arrayBuffer);
  const length = Math.floor(arrayBuffer.byteLength / 2);
  const result = new Float32Array(length);
  for (let i = 0; i < length; i++) {
    const intSample = view.getInt16(i * 2, true);
    result[i] = intSample < 0 ? intSample / 0x8000 : intSample / 0x7fff;
  }
  return result;
}

export default {
  downsampleTo16k,
  floatTo16BitPCM,
  int16ToFloat32,
};
