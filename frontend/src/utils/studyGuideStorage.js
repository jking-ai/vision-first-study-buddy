/**
 * Study guide persistence for saving and retrieving generated study guides.
 *
 * Stores study guides in localStorage with user-assigned display names.
 */

const STORAGE_KEY = "vfsb_saved_study_guides";

/**
 * Get all saved study guides from localStorage.
 * @returns {Array<{id: string, displayName: string, studyGuide: Object, savedAt: string}>}
 */
export function getSavedStudyGuides() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
}

/**
 * Save a study guide to localStorage.
 * @param {Object} studyGuide - The study guide object from the API
 * @param {string} displayName - User-assigned display name
 * @returns {string} The saved entry ID
 */
export function saveStudyGuide(studyGuide, displayName) {
  const guides = getSavedStudyGuides();
  const entryId = `saved_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  
  const entry = {
    id: entryId,
    displayName: displayName || studyGuide.title,
    studyGuide,
    savedAt: new Date().toISOString(),
  };
  
  guides.unshift(entry);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(guides));
  return entryId;
}

/**
 * Get a single saved study guide by ID.
 * @param {string} id - The saved entry ID
 * @returns {Object|null} The saved entry or null if not found
 */
export function getSavedStudyGuide(id) {
  const guides = getSavedStudyGuides();
  return guides.find((g) => g.id === id) || null;
}

/**
 * Update the display name of a saved study guide.
 * @param {string} id - The saved entry ID
 * @param {string} displayName - New display name
 */
export function updateStudyGuideName(id, displayName) {
  const guides = getSavedStudyGuides();
  const index = guides.findIndex((g) => g.id === id);
  if (index !== -1) {
    guides[index].displayName = displayName;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(guides));
  }
}

/**
 * Delete a saved study guide.
 * @param {string} id - The saved entry ID
 */
export function deleteStudyGuide(id) {
  const guides = getSavedStudyGuides();
  const filtered = guides.filter((g) => g.id !== id);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered));
}

/**
 * Clear all saved study guides.
 */
export function clearAllStudyGuides() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify([]));
}

export default {
  getSavedStudyGuides,
  saveStudyGuide,
  getSavedStudyGuide,
  updateStudyGuideName,
  deleteStudyGuide,
  clearAllStudyGuides,
};
