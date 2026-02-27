/**
 * Quiz score history persistence.
 *
 * Stores quiz results in localStorage for historical tracking.
 */

const STORAGE_KEY = "vfsb_quiz_history";

/**
 * Get all quiz history from localStorage.
 * @returns {Array<{id: string, quizId: string, title: string, score: number, total: number, percentage: number, date: string}>}
 */
export function getQuizHistory() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
}

/**
 * Save a quiz result to history.
 * @param {{quizId: string, title: string, score: number, total: number, percentage: number}} result
 * @returns {string} The history entry ID
 */
export function saveQuizResult(result) {
  const history = getQuizHistory();
  const entryId = `hist_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  
  const entry = {
    id: entryId,
    quizId: result.quizId,
    title: result.title,
    score: result.score,
    total: result.total,
    percentage: result.percentage,
    date: new Date().toISOString(),
  };
  
  history.unshift(entry);
  
  const MAX_HISTORY = 50;
  if (history.length > MAX_HISTORY) {
    history.length = MAX_HISTORY;
  }
  
  localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
  return entryId;
}

/**
 * Delete a specific history entry.
 * @param {string} id - The history entry ID
 */
export function deleteHistoryEntry(id) {
  const history = getQuizHistory();
  const filtered = history.filter((h) => h.id !== id);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered));
}

/**
 * Clear all quiz history.
 */
export function clearQuizHistory() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify([]));
}

/**
 * Get statistics from quiz history.
 * @returns {{totalQuizzes: number, averageScore: number, bestScore: number}}
 */
export function getQuizStats() {
  const history = getQuizHistory();
  if (history.length === 0) {
    return { totalQuizzes: 0, averageScore: 0, bestScore: 0 };
  }
  
  const percentages = history.map((h) => h.percentage);
  const totalQuizzes = history.length;
  const averageScore = percentages.reduce((a, b) => a + b, 0) / percentages.length;
  const bestScore = Math.max(...percentages);
  
  return {
    totalQuizzes,
    averageScore: Math.round(averageScore * 10) / 10,
    bestScore,
  };
}

export default {
  getQuizHistory,
  saveQuizResult,
  deleteHistoryEntry,
  clearQuizHistory,
  getQuizStats,
};
