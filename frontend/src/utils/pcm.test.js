import { describe, it, expect } from "vitest";
import { downsampleTo16k, floatTo16BitPCM, int16ToFloat32 } from "./pcm";

describe("pcm utilities", () => {
  it("downsamples 48k to 16k", () => {
    const input = new Float32Array(4800);
    for (let i = 0; i < input.length; i++) {
      input[i] = Math.sin((i / 4800) * Math.PI * 2);
    }
    const output = downsampleTo16k(input, 48000);
    expect(output.length).toBe(1600);

    // Unchanged when sample rate is 16000
    const unchanged = downsampleTo16k(input, 16000);
    expect(unchanged).toBe(input);
  });

  it("converts float to 16-bit PCM correctly", () => {
    const input = new Float32Array([1.0, -1.0, 0.0, 0.5, -0.5]);
    const buffer = floatTo16BitPCM(input);
    const view = new DataView(buffer);

    expect(view.getInt16(0, true)).toBe(32767);
    expect(view.getInt16(2, true)).toBe(-32768);
    expect(view.getInt16(4, true)).toBe(0);
  });

  it("performs accurate round trip conversion", () => {
    const testValues = [0.0, 0.25, -0.25, 0.5, -0.5, 0.75, -0.75, 1.0, -1.0];
    const input = new Float32Array(testValues);
    const pcmBuffer = floatTo16BitPCM(input);
    const reconstructed = int16ToFloat32(pcmBuffer);

    expect(reconstructed.length).toBe(input.length);
    const tolerance = 1 / 32768;
    for (let i = 0; i < input.length; i++) {
      expect(Math.abs(reconstructed[i] - input[i])).toBeLessThanOrEqual(tolerance);
    }
  });
});
