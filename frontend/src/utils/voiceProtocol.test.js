import { describe, it, expect } from "vitest";
import {
  initialVoiceState,
  reduceVoiceMessage,
  getVoiceErrorMessage,
  createVoiceQuizHistoryPayload,
} from "./voiceProtocol";

describe("voiceProtocol", () => {
  it("ready sets secondsLeft and sessionId", () => {
    const readyMsg = {
      type: "ready",
      session_id: "vs_12345678",
      max_duration_s: 180,
      voice: "Kore",
    };
    const nextState = reduceVoiceMessage(initialVoiceState, readyMsg);
    expect(nextState.state).toBe("ready");
    expect(nextState.secondsLeft).toBe(180);
    expect(nextState.sessionId).toBe("vs_12345678");
  });

  it("marks the previous speaker's entry complete when a new speaker starts", () => {
    let state = initialVoiceState;
    state = reduceVoiceMessage(state, { type: "transcript", role: "user", text: "Cytoplasm" });
    expect(state.transcript[0].completed).toBe(false);
    state = reduceVoiceMessage(state, { type: "transcript", role: "coach", text: "Right." });
    expect(state.transcript.length).toBe(2);
    expect(state.transcript[0].completed).toBe(true);
    expect(state.transcript[1].completed).toBe(false);
  });

  it("time_up zeroes the clock and locks input without ending the session", () => {
    let state = reduceVoiceMessage(initialVoiceState, {
      type: "ready",
      session_id: "vs_1",
      max_duration_s: 180,
    });
    state = reduceVoiceMessage(state, { type: "time_up", grace_s: 30 });
    expect(state.state).toBe("ready");
    expect(state.secondsLeft).toBe(0);
    expect(state.inputLocked).toBe(true);
  });

  it("ended completes every transcript entry", () => {
    let state = initialVoiceState;
    state = reduceVoiceMessage(state, { type: "transcript", role: "coach", text: "Bye" });
    state = reduceVoiceMessage(state, { type: "ended", reason: "max_duration" });
    expect(state.state).toBe("ended");
    expect(state.transcript.every((e) => e.completed)).toBe(true);
  });

  it("merges two consecutive coach transcripts into one line", () => {
    let state = initialVoiceState;
    state = reduceVoiceMessage(state, {
      type: "transcript",
      role: "coach",
      text: "Hello ",
    });
    state = reduceVoiceMessage(state, {
      type: "transcript",
      role: "coach",
      text: "there!",
    });

    expect(state.transcript.length).toBe(1);
    expect(state.transcript[0].text).toBe("Hello there!");
    expect(state.transcript[0].role).toBe("coach");
  });

  it("turn_complete then new coach transcript starts a new line", () => {
    let state = initialVoiceState;
    state = reduceVoiceMessage(state, {
      type: "transcript",
      role: "coach",
      text: "First turn.",
    });
    state = reduceVoiceMessage(state, { type: "turn_complete" });
    state = reduceVoiceMessage(state, {
      type: "transcript",
      role: "coach",
      text: "Second turn.",
    });

    expect(state.transcript.length).toBe(2);
    expect(state.transcript[0].text).toBe("First turn.");
    expect(state.transcript[1].text).toBe("Second turn.");
  });

  it("interrupted sets a clearPlayback flag", () => {
    let state = initialVoiceState;
    state = reduceVoiceMessage(state, { type: "interrupted" });
    expect(state.clearPlayback).toBe(true);
  });

  it("maps close code 4429 with DEVICE_DAILY_LIMIT to exact message", () => {
    const msg = getVoiceErrorMessage(4429, "DEVICE_DAILY_LIMIT");
    expect(msg).toBe(
      "You've used today's voice sessions on this device. Come back tomorrow."
    );
  });

  it("maps all error codes correctly", () => {
    expect(getVoiceErrorMessage(4429, "GLOBAL_DAILY_LIMIT")).toBe(
      "The voice coach is fully booked today. Try again tomorrow."
    );
    expect(getVoiceErrorMessage(4429, "CONCURRENT_LIMIT")).toBe(
      "The coach is busy with other students right now. Try again in a few minutes."
    );
    expect(getVoiceErrorMessage(4429, "AUDIO_QUOTA_EXCEEDED")).toBe(
      "This session sent more audio than allowed and was ended."
    );
    expect(getVoiceErrorMessage(4503, "VOICE_DISABLED")).toBe(
      "Voice mode is turned off right now."
    );
    expect(getVoiceErrorMessage(4408, "START_TIMEOUT")).toBe(
      "The connection timed out before the session started."
    );
    expect(getVoiceErrorMessage(1011, "UPSTREAM_ERROR")).toBe(
      "The voice service hit an error. Please try again."
    );
    expect(getVoiceErrorMessage("MIC_DENIED")).toBe(
      "Microphone access is needed for voice mode. Allow it in your browser settings."
    );
    expect(getVoiceErrorMessage("AUDIO_UNSUPPORTED")).toBe(
      "Your browser doesn't support the audio features voice mode needs."
    );
  });

  it("answer_recorded updates score and records answer", () => {
    let state = initialVoiceState;
    const answerMsg = {
      type: "answer_recorded",
      index: 1,
      question: "What is photosynthesis?",
      student_answer: "Plants making food",
      correct: true,
      feedback: "Great explanation!",
      score: { correct: 1, total: 5 },
    };
    state = reduceVoiceMessage(state, answerMsg);

    expect(state.answers.length).toBe(1);
    expect(state.answers[0].question).toBe("What is photosynthesis?");
    expect(state.score).toEqual({ correct: 1, total: 5 });
  });

  it("quiz_summary produces a saveHistory payload with mode: 'voice' and correct percentage", () => {
    let state = {
      ...initialVoiceState,
      sessionId: "vs_test_session",
      score: { correct: 4, total: 5 },
    };
    const summaryMsg = {
      type: "quiz_summary",
      summary: "Excellent understanding of the core topics.",
      score: { correct: 4, asked: 5, total: 5 },
    };
    state = reduceVoiceMessage(state, summaryMsg);
    expect(state.quizSummary).toBe("Excellent understanding of the core topics.");

    const historyPayload = createVoiceQuizHistoryPayload(state, {
      title: "Cell Biology",
    });
    expect(historyPayload).toEqual({
      quizId: "vs_test_session",
      title: "Voice: Cell Biology",
      score: 4,
      total: 5,
      percentage: 80,
      mode: "voice",
    });
  });
});
