import { useState, useEffect, useRef, useCallback } from "react";
import { apiClient } from "../api/client";
import { getDeviceId } from "../utils/deviceId";
import { downsampleTo16k, floatTo16BitPCM, int16ToFloat32 } from "../utils/pcm";
import {
  initialVoiceState,
  reduceVoiceMessage,
  getVoiceErrorMessage,
  createVoiceQuizHistoryPayload,
} from "../utils/voiceProtocol";
import { saveQuizResult } from "../utils/quizHistory";

// Upper bound on how long queued coach audio may keep playing after the session ends.
const MAX_DRAIN_MS = 20000;

export function useVoiceSession({ studyGuide, voice } = {}) {
  const [sessionState, setSessionState] = useState(initialVoiceState);
  const [status, setStatus] = useState(null);
  const [isTalking, setIsTalking] = useState(false);

  // References to preserve state across callbacks without re-triggering effects
  const wsRef = useRef(null);
  const playbackContextRef = useRef(null);
  const captureContextRef = useRef(null);
  const micStreamRef = useRef(null);
  const workletNodeRef = useRef(null);
  const activeSourcesRef = useRef([]);
  const nextStartTimeRef = useRef(0);
  const isTalkingRef = useRef(false);
  const audioSampleBufferRef = useRef([]);
  const studyGuideRef = useRef(studyGuide);
  const sessionStateRef = useRef(sessionState);
  const pendingEndedRef = useRef(null);

  studyGuideRef.current = studyGuide;
  sessionStateRef.current = sessionState;

  const refreshStatus = useCallback(async () => {
    try {
      const res = await apiClient.getVoiceStatus();
      setStatus(res);
      return res;
    } catch {
      setStatus(null);
    }
  }, []);

  useEffect(() => {
    refreshStatus();
  }, [refreshStatus]);

  /**
   * Release mic and audio resources.
   *
   * With `drainPlayback`, audio the coach has already sent keeps playing until
   * the queue is empty (bounded by MAX_DRAIN_MS) instead of being cut off.
   * Returns the number of milliseconds of playback still queued.
   */
  const cleanupAudio = useCallback(({ drainPlayback = false } = {}) => {
    const playback = playbackContextRef.current;
    let remainingMs = 0;
    if (drainPlayback && playback && playback.state !== "closed") {
      remainingMs = Math.max(
        0,
        Math.min(MAX_DRAIN_MS, (nextStartTimeRef.current - playback.currentTime) * 1000)
      );
    }

    if (!drainPlayback) {
      // Stop playing sources
      activeSourcesRef.current.forEach((src) => {
        try {
          src.stop();
        } catch {}
      });
      activeSourcesRef.current = [];
    }

    // Stop mic stream
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach((t) => t.stop());
      micStreamRef.current = null;
    }

    // Disconnect worklet
    if (workletNodeRef.current) {
      workletNodeRef.current.disconnect();
      workletNodeRef.current = null;
    }

    // Close AudioContexts
    if (captureContextRef.current && captureContextRef.current.state !== "closed") {
      captureContextRef.current.close().catch(() => {});
      captureContextRef.current = null;
    }
    if (playback && playback.state !== "closed") {
      playbackContextRef.current = null;
      const closePlayback = () => {
        activeSourcesRef.current = [];
        playback.close().catch(() => {});
      };
      if (remainingMs > 0) {
        setTimeout(closePlayback, remainingMs + 100);
      } else {
        closePlayback();
      }
    }
    return remainingMs;
  }, []);

  const end = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      try {
        wsRef.current.send(JSON.stringify({ type: "end" }));
      } catch {}
    }
  }, []);

  const pressTalk = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    if (isTalkingRef.current) return;
    if (sessionStateRef.current.inputLocked) return;

    // Resume playback context if needed
    if (playbackContextRef.current?.state === "suspended") {
      playbackContextRef.current.resume();
    }
    if (captureContextRef.current?.state === "suspended") {
      captureContextRef.current.resume();
    }

    isTalkingRef.current = true;
    setIsTalking(true);
    audioSampleBufferRef.current = [];
    wsRef.current.send(JSON.stringify({ type: "speech_start" }));
  }, []);

  const releaseTalk = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    if (!isTalkingRef.current) return;

    isTalkingRef.current = false;
    setIsTalking(false);

    // Send residual buffer if present
    if (audioSampleBufferRef.current.length > 0) {
      const remaining = Float32Array.from(audioSampleBufferRef.current);
      audioSampleBufferRef.current = [];
      const pcm = floatTo16BitPCM(remaining);
      try {
        wsRef.current.send(pcm);
      } catch {}
    }

    wsRef.current.send(JSON.stringify({ type: "speech_end" }));
  }, []);

  const start = useCallback(async () => {
    if (!studyGuideRef.current) return;

    setSessionState({
      ...initialVoiceState,
      state: "connecting",
    });

    try {
      // 1. Audio context for playback (24 kHz mono)
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) {
        throw new Error("AUDIO_UNSUPPORTED");
      }

      playbackContextRef.current = new AudioCtx({ sampleRate: 24000 });
      await playbackContextRef.current.resume();
      nextStartTimeRef.current = playbackContextRef.current.currentTime;

      // 2. Audio context for microphone capture
      captureContextRef.current = new AudioCtx();
      await captureContextRef.current.resume();

      // 3. Request user media
      let stream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
        });
        micStreamRef.current = stream;
      } catch {
        throw new Error("MIC_DENIED");
      }

      // 4. Load AudioWorklet
      try {
        await captureContextRef.current.audioWorklet.addModule(
          "/worklets/pcm-recorder.worklet.js"
        );
      } catch {
        throw new Error("AUDIO_UNSUPPORTED");
      }

      const sourceNode = captureContextRef.current.createMediaStreamSource(stream);
      const workletNode = new AudioWorkletNode(
        captureContextRef.current,
        "pcm-recorder"
      );
      workletNodeRef.current = workletNode;
      sourceNode.connect(workletNode);

      // Handle raw mic audio from worklet
      workletNode.port.onmessage = (event) => {
        if (!isTalkingRef.current) return;
        const rawChunk = event.data;
        if (!rawChunk || rawChunk.length === 0) return;

        const downsampled = downsampleTo16k(
          rawChunk,
          captureContextRef.current?.sampleRate || 48000
        );

        for (let i = 0; i < downsampled.length; i++) {
          audioSampleBufferRef.current.push(downsampled[i]);
        }

        while (audioSampleBufferRef.current.length >= 4096) {
          const slice = audioSampleBufferRef.current.splice(0, 4096);
          const pcm = floatTo16BitPCM(Float32Array.from(slice));
          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(pcm);
          }
        }
      };

      // 5. Open WebSocket
      const httpBase = import.meta.env.VITE_API_URL || window.location.origin;
      const wsUrl = httpBase.replace(/^http/, "ws") + "/api/v1/voice/session";
      const ws = new WebSocket(wsUrl);
      ws.binaryType = "arraybuffer";
      wsRef.current = ws;

      ws.onopen = () => {
        const startPayload = {
          type: "start",
          device_id: getDeviceId(),
          study_guide: studyGuideRef.current,
          voice: voice || undefined,
        };
        ws.send(JSON.stringify(startPayload));
      };

      ws.onmessage = (event) => {
        if (event.data instanceof ArrayBuffer) {
          // Playback audio: 24kHz Int16 LE
          const float32 = int16ToFloat32(event.data);
          const ctx = playbackContextRef.current;
          if (!ctx) return;

          const buffer = ctx.createBuffer(1, float32.length, 24000);
          buffer.copyToChannel(float32, 0);

          const source = ctx.createBufferSource();
          source.buffer = buffer;
          source.connect(ctx.destination);

          const currentTime = ctx.currentTime;
          const startTime = Math.max(currentTime, nextStartTimeRef.current);
          source.start(startTime);
          nextStartTimeRef.current = startTime + buffer.duration;
          activeSourcesRef.current.push(source);

          source.onended = () => {
            activeSourcesRef.current = activeSourcesRef.current.filter((s) => s !== source);
          };
          return;
        }

        // Text frame
        try {
          const msg = JSON.parse(event.data);

          if (msg.type === "interrupted") {
            activeSourcesRef.current.forEach((src) => {
              try {
                src.stop();
              } catch {}
            });
            activeSourcesRef.current = [];
            nextStartTimeRef.current = playbackContextRef.current?.currentTime || 0;
          }

          if (msg.type === "ended") {
            // Lock input now, but keep the live view up until the coach's
            // queued audio has finished playing.
            setSessionState((prev) => ({ ...prev, inputLocked: true }));
            pendingEndedRef.current = msg;
            return;
          }

          setSessionState((prev) => {
            const next = reduceVoiceMessage(prev, msg);
            if (msg.type === "quiz_summary" && studyGuideRef.current) {
              // Automatically save quiz result to history
              const payload = createVoiceQuizHistoryPayload(next, studyGuideRef.current);
              saveQuizResult(payload);
            }
            return next;
          });
        } catch {}
      };

      ws.onclose = (event) => {
        refreshStatus();

        if (event.code !== 1000) {
          cleanupAudio();
          setSessionState((prev) => ({
            ...prev,
            state: "error",
            error: {
              code: event.code,
              message: getVoiceErrorMessage(event.code),
            },
          }));
          return;
        }

        const endedMsg = pendingEndedRef.current || { type: "ended", reason: "client_end" };
        pendingEndedRef.current = null;
        const remainingMs = cleanupAudio({ drainPlayback: true });
        const finish = () => {
          setSessionState((prev) => reduceVoiceMessage(prev, endedMsg));
        };
        if (remainingMs > 0) {
          setTimeout(finish, remainingMs);
        } else {
          finish();
        }
      };

      ws.onerror = () => {
        cleanupAudio();
        setSessionState((prev) => ({
          ...prev,
          state: "error",
          error: {
            code: 1011,
            message: getVoiceErrorMessage(1011),
          },
        }));
      };
    } catch (err) {
      cleanupAudio();
      const code = err.message in { MIC_DENIED: 1, AUDIO_UNSUPPORTED: 1 } ? err.message : 4400;
      setSessionState((prev) => ({
        ...prev,
        state: "error",
        error: {
          code,
          message: getVoiceErrorMessage(code),
        },
      }));
    }
  }, [voice, cleanupAudio, refreshStatus]);

  // Countdown timer when session is ready/active
  useEffect(() => {
    if (sessionState.state !== "ready" && sessionState.state !== "talking") return;
    if (sessionState.secondsLeft === null || sessionState.secondsLeft <= 0) return;

    const timer = setInterval(() => {
      setSessionState((prev) => {
        if (prev.secondsLeft === null || prev.secondsLeft <= 1) {
          // Time is up for the student. The server locks input and lets the
          // coach finish its turn before sending "ended".
          clearInterval(timer);
          return {
            ...prev,
            secondsLeft: 0,
            inputLocked: true,
          };
        }
        return {
          ...prev,
          secondsLeft: prev.secondsLeft - 1,
        };
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [sessionState.state, sessionState.secondsLeft]);

  // Cleanup on component unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      cleanupAudio();
    };
  }, [cleanupAudio]);

  // If time runs out mid-answer, finish the utterance so the coach can respond.
  useEffect(() => {
    if (sessionState.inputLocked && isTalkingRef.current) {
      releaseTalk();
    }
  }, [sessionState.inputLocked, releaseTalk]);

  const effectiveState = isTalking ? "talking" : sessionState.state;

  return {
    state: effectiveState,
    status,
    transcript: sessionState.transcript,
    secondsLeft: sessionState.secondsLeft,
    inputLocked: sessionState.inputLocked,
    error: sessionState.error,
    endedReason: sessionState.endedReason,
    answers: sessionState.answers,
    quizSummary: sessionState.quizSummary,
    score: sessionState.score,
    start,
    pressTalk,
    releaseTalk,
    end,
    refreshStatus,
  };
}

export default useVoiceSession;
