import { useState, useEffect, useCallback } from "react";
import apiClient from "../api/client";
import {
  getSavedStudyGuides,
  saveStudyGuide as saveToStorage,
  deleteStudyGuide as deleteFromStorage,
  updateStudyGuideName,
} from "../utils/studyGuideStorage";

/**
 * Custom hook for study guide generation, saving, and retrieval.
 *
 * @returns {{
 *   generate: Function,
 *   studyGuide: object|null,
 *   loading: boolean,
 *   error: string|null,
 *   reset: Function,
 *   savedGuides: Array,
 *   save: Function,
 *   loadSaved: Function,
 *   deleteSaved: Function,
 *   renameSaved: Function,
 *   refreshSaved: Function
 * }}
 */
export function useStudyGuide() {
  const [studyGuide, setStudyGuide] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [savedGuides, setSavedGuides] = useState([]);

  const refreshSaved = useCallback(() => {
    setSavedGuides(getSavedStudyGuides());
  }, []);

  useEffect(() => {
    refreshSaved();
  }, [refreshSaved]);

  const generate = async (materialIds, focusTopics, detailLevel) => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.generateStudyGuide(
        materialIds,
        focusTopics || [],
        detailLevel || "standard"
      );
      setStudyGuide(data.study_guide);
      return data;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setStudyGuide(null);
    setError(null);
  };

  const save = (guide, displayName) => {
    const guideToSave = guide || studyGuide;
    if (!guideToSave) return null;
    const id = saveToStorage(guideToSave, displayName || guideToSave.title);
    refreshSaved();
    return id;
  };

  const loadSaved = (savedEntry) => {
    if (savedEntry?.studyGuide) {
      setStudyGuide(savedEntry.studyGuide);
      setError(null);
    }
  };

  const deleteSaved = (id) => {
    deleteFromStorage(id);
    refreshSaved();
  };

  const renameSaved = (id, newName) => {
    updateStudyGuideName(id, newName);
    refreshSaved();
  };

  return {
    generate,
    studyGuide,
    loading,
    error,
    reset,
    savedGuides,
    save,
    loadSaved,
    deleteSaved,
    renameSaved,
    refreshSaved,
  };
}

export default useStudyGuide;
