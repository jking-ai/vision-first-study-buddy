/**
 * Protocol handling, state reducer, and close code mappings for Voice Mode.
 */

export const ERROR_MESSAGES = {
  DEVICE_DAILY_LIMIT: "You've used today's voice sessions on this device. Come back tomorrow.",
  GLOBAL_DAILY_LIMIT: "The voice coach is fully booked today. Try again tomorrow.",
  CONCURRENT_LIMIT: "The coach is busy with other students right now. Try again in a few minutes.",
  AUDIO_QUOTA_EXCEEDED: "This session sent more audio than allowed and was ended.",
  VOICE_DISABLED: "Voice mode is turned off right now.",
  START_TIMEOUT: "The connection timed out before the session started.",
  UPSTREAM_ERROR: "The voice service hit an error. Please try again.",
  MIC_DENIED: "Microphone access is needed for voice mode. Allow it in your browser settings.",
  AUDIO_UNSUPPORTED: "Your browser doesn't support the audio features voice mode needs.",
};

/**
 * Map WebSocket close code or application error code to user-facing message.
 * @param {number|string} code - WebSocket close code or error code string
 * @param {string} [errorCode] - Error code in server error frame (e.g. DEVICE_DAILY_LIMIT)
 * @returns {string} User-facing error message
 */
export function getVoiceErrorMessage(code, errorCode) {
  if (errorCode && ERROR_MESSAGES[errorCode]) {
    return ERROR_MESSAGES[errorCode];
  }
  if (typeof code === "string" && ERROR_MESSAGES[code]) {
    return ERROR_MESSAGES[code];
  }

  const numCode = Number(code);
  switch (numCode) {
    case 4429:
      if (errorCode === "DEVICE_DAILY_LIMIT") return ERROR_MESSAGES.DEVICE_DAILY_LIMIT;
      if (errorCode === "GLOBAL_DAILY_LIMIT") return ERROR_MESSAGES.GLOBAL_DAILY_LIMIT;
      if (errorCode === "CONCURRENT_LIMIT") return ERROR_MESSAGES.CONCURRENT_LIMIT;
      if (errorCode === "AUDIO_QUOTA_EXCEEDED") return ERROR_MESSAGES.AUDIO_QUOTA_EXCEEDED;
      return "Rate limit exceeded. Please try again later.";
    case 4503:
      return ERROR_MESSAGES.VOICE_DISABLED;
    case 4408:
      return ERROR_MESSAGES.START_TIMEOUT;
    case 4400:
    case 4401:
    case 4403:
      return "Something went wrong starting the session.";
    case 1011:
      return ERROR_MESSAGES.UPSTREAM_ERROR;
    default:
      return "Something went wrong starting the session.";
  }
}

export const initialVoiceState = {
  state: "idle", // "idle" | "checking" | "connecting" | "ready" | "talking" | "ended" | "error"
  secondsLeft: null,
  sessionId: null,
  voice: "Kore",
  transcript: [], // [{ role: "user" | "coach", text: string, completed: boolean }]
  clearPlayback: false,
  answers: [], // [{ index, question, student_answer, correct, feedback }]
  score: null, // { correct, total }
  quizSummary: null,
  endedReason: null,
  error: null,
};

/**
 * Pure reducer handling incoming server messages for voice session state.
 * @param {typeof initialVoiceState} prevState
 * @param {object} message
 * @returns {typeof initialVoiceState}
 */
export function reduceVoiceMessage(prevState, message) {
  if (!message || !message.type) return prevState;

  switch (message.type) {
    case "ready":
      return {
        ...prevState,
        state: "ready",
        sessionId: message.session_id,
        secondsLeft: message.max_duration_s,
        voice: message.voice || prevState.voice,
        clearPlayback: false,
      };

    case "transcript": {
      const transcript = [...prevState.transcript];
      const last = transcript.length > 0 ? transcript[transcript.length - 1] : null;

      if (last && last.role === message.role && !last.completed) {
        transcript[transcript.length - 1] = {
          ...last,
          text: last.text + message.text,
        };
      } else {
        transcript.push({
          role: message.role,
          text: message.text,
          completed: false,
        });
      }

      return {
        ...prevState,
        transcript,
        clearPlayback: false,
      };
    }

    case "turn_complete": {
      const transcript = [...prevState.transcript];
      if (transcript.length > 0) {
        const last = transcript[transcript.length - 1];
        transcript[transcript.length - 1] = {
          ...last,
          completed: true,
        };
      }
      return {
        ...prevState,
        transcript,
      };
    }

    case "interrupted":
      return {
        ...prevState,
        clearPlayback: true,
      };

    case "answer_recorded": {
      const answers = [
        ...prevState.answers,
        {
          index: message.index,
          question: message.question,
          student_answer: message.student_answer,
          correct: message.correct,
          feedback: message.feedback,
        },
      ];
      return {
        ...prevState,
        answers,
        score: {
          correct: message.score.correct,
          total: message.score.total,
        },
      };
    }

    case "quiz_summary":
      return {
        ...prevState,
        quizSummary: message.summary,
        score: {
          correct: message.score.correct,
          total: message.score.total,
        },
      };

    case "ended":
      return {
        ...prevState,
        state: "ended",
        endedReason: message.reason,
      };

    case "error":
      return {
        ...prevState,
        state: "error",
        error: {
          code: message.code,
          message: getVoiceErrorMessage(null, message.code) || message.message,
        },
      };

    default:
      return prevState;
  }
}

/**
 * Format score history payload for voice sessions.
 * @param {object} voiceState
 * @param {object} studyGuide
 * @returns {object} Payload suitable for saveQuizResult
 */
export function createVoiceQuizHistoryPayload(voiceState, studyGuide) {
  const correct = voiceState.score?.correct || 0;
  const total = voiceState.score?.total || 5;
  const percentage = Math.round((100 * correct) / total);

  return {
    quizId: voiceState.sessionId || `voice_${Date.now()}`,
    title: `Voice: ${studyGuide?.title || "Study Guide"}`,
    score: correct,
    total: total,
    percentage: percentage,
    mode: "voice",
  };
}

export default {
  ERROR_MESSAGES,
  getVoiceErrorMessage,
  initialVoiceState,
  reduceVoiceMessage,
  createVoiceQuizHistoryPayload,
};
