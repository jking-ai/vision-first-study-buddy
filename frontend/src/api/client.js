/**
 * API client for Vision-First Study Buddy backend.
 *
 * Wraps fetch calls to the FastAPI backend with error handling
 * and response parsing.
 *
 * TODO: Implement all API methods
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const API_PREFIX = "/api/v1";

/**
 * Make a request to the backend API.
 * @param {string} path - API path (e.g., "/health")
 * @param {object} options - Fetch options
 * @returns {Promise<object>} Parsed JSON response
 */
async function request(path, options = {}) {
  // TODO: Implement base request function
  // 1. Build full URL from API_BASE_URL + API_PREFIX + path
  // 2. Set default headers (Content-Type: application/json)
  // 3. Make fetch call
  // 4. Handle error responses (parse error body, throw with message)
  // 5. Parse and return JSON response
  throw new Error("API client not yet implemented");
}

export const apiClient = {
  /** Health check */
  health: () => {
    // TODO: return request("/health");
    throw new Error("Not implemented");
  },

  /** Upload files */
  uploadMaterials: (files) => {
    // TODO: Build FormData and POST to /materials/upload
    // const formData = new FormData();
    // files.forEach((file) => formData.append("files", file));
    // return request("/materials/upload", { method: "POST", body: formData });
    throw new Error("Not implemented");
  },

  /** List all materials */
  listMaterials: () => {
    // TODO: return request("/materials");
    throw new Error("Not implemented");
  },

  /** Get material details */
  getMaterial: (id) => {
    // TODO: return request(`/materials/${id}`);
    throw new Error("Not implemented");
  },

  /** Generate a study guide */
  generateStudyGuide: (materialIds, focusTopics, detailLevel) => {
    // TODO: POST to /study-guides/generate with request body
    throw new Error("Not implemented");
  },

  /** Get a study guide */
  getStudyGuide: (id) => {
    // TODO: return request(`/study-guides/${id}`);
    throw new Error("Not implemented");
  },

  /** Generate a quiz */
  generateQuiz: (materialIds, numQuestions, difficulty, questionTypes) => {
    // TODO: POST to /quizzes/generate with request body
    throw new Error("Not implemented");
  },

  /** Get a quiz */
  getQuiz: (id) => {
    // TODO: return request(`/quizzes/${id}`);
    throw new Error("Not implemented");
  },

  /** Submit quiz answers */
  submitQuiz: (quizId, answers) => {
    // TODO: POST to /quizzes/{quizId}/submit with answers
    throw new Error("Not implemented");
  },
};

export default apiClient;
