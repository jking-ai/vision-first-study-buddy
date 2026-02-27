/**
 * Material labels management for custom display names.
 *
 * Stores user-assigned labels for materials in localStorage.
 * Labels are displayed instead of filenames when set.
 */

const STORAGE_KEY = "vfsb_material_labels";

/**
 * Get all material labels from localStorage.
 * @returns {Object.<string, string>} Map of materialId to label
 */
export function getAllLabels() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : {};
  } catch {
    return {};
  }
}

/**
 * Get the label for a specific material.
 * @param {string} materialId - The material ID
 * @returns {string|null} The label, or null if not set
 */
export function getLabel(materialId) {
  const labels = getAllLabels();
  return labels[materialId] || null;
}

/**
 * Set the label for a specific material.
 * @param {string} materialId - The material ID
 * @param {string} label - The label to set (empty string removes the label)
 */
export function setLabel(materialId, label) {
  const labels = getAllLabels();
  if (label && label.trim()) {
    labels[materialId] = label.trim();
  } else {
    delete labels[materialId];
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(labels));
}

/**
 * Remove the label for a specific material.
 * @param {string} materialId - The material ID
 */
export function removeLabel(materialId) {
  setLabel(materialId, "");
}

export default { getAllLabels, getLabel, setLabel, removeLabel };
