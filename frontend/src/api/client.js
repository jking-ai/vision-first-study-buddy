/**
 * API client for Vision-First Study Buddy backend.
 *
 * Wraps fetch calls to the FastAPI backend with error handling
 * and response parsing.
 */

import { getDeviceId } from "../utils/deviceId";

const API_BASE_URL = import.meta.env.VITE_API_URL || "";
const API_PREFIX = "/api/v1";

/**
 * Make a request to the backend API.
 * @param {string} path - API path (e.g., "/health")
 * @param {object} options - Fetch options
 * @returns {Promise<object>} Parsed JSON response
 */
async function request(path, options = {}) {
  const url = `${API_BASE_URL}${API_PREFIX}${path}`;

  const headers = { ...options.headers };
  // Add device ID header for per-device material isolation
  headers["X-Device-ID"] = getDeviceId();
  // Only set Content-Type for JSON bodies; omit for FormData so the browser
  // sets the multipart boundary automatically.
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  let response;
  try {
    response = await fetch(url, { ...options, headers });
  } catch {
    throw new Error("Network error — is the backend running?");
  }

  if (!response.ok) {
    let message = response.statusText;
    try {
      const body = await response.json();
      message = body.detail || body.message || message;
    } catch {
      // ignore parse errors; use statusText
    }
    throw new Error(message);
  }

  return response.json();
}

export const apiClient = {
  /** Health check */
  health: () => request("/health"),

  /** Upload files to Firebase Storage */
  uploadMaterials: (files) => {
    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));
    return request("/materials/upload", { method: "POST", body: formData });
  },

  /** List all uploaded materials */
  listMaterials: () => request("/materials"),

  /** Get details for a single material */
  getMaterial: (id) => request(`/materials/${id}`),

  /** Generate a study guide from selected materials */
  generateStudyGuide: (materialIds, focusTopics, detailLevel) =>
    request("/study-guides/generate", {
      method: "POST",
      body: JSON.stringify({ material_ids: materialIds, focus_topics: focusTopics, detail_level: detailLevel }),
    }),

  /** Retrieve a generated study guide */
  getStudyGuide: (id) => request(`/study-guides/${id}`),

  /** Generate a quiz from selected materials */
  generateQuiz: (materialIds, numQuestions, difficulty, questionTypes) =>
    request("/quizzes/generate", {
      method: "POST",
      body: JSON.stringify({
        material_ids: materialIds,
        num_questions: numQuestions,
        difficulty,
        question_types: questionTypes,
      }),
    }),

  /** Retrieve a generated quiz */
  getQuiz: (id) => request(`/quizzes/${id}`),

  /** Submit quiz answers for grading */
  submitQuiz: (quizId, answers) =>
    request(`/quizzes/${quizId}/submit`, {
      method: "POST",
      body: JSON.stringify({ answers }),
    }),

  /** Get voice status and session caps */
  getVoiceStatus: () => request("/voice/status"),
};

export default apiClient;
