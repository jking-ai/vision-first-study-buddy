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
 * Every generated guide is saved to localStorage the moment it arrives, named
 * by its title. Generation is the expensive step (a rate-limited Gemini call);
 * saving is free, so nothing is ever lost by navigating away.
 *
 * @returns {{
 *   generate: Function,
 *   studyGuide: object|null,
 *   currentEntry: object|null,  // the saved entry backing the guide in view
 *   loading: boolean,
 *   error: string|null,
 *   reset: Function,
 *   savedGuides: Array,
 *   loadSaved: Function,
 *   deleteSaved: Function,
 *   renameSaved: Function,
 *   refreshSaved: Function
 * }}
 */
export function useStudyGuide() {
  const [studyGuide, setStudyGuide] = useState(null);
  const [currentEntryId, setCurrentEntryId] = useState(null);
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
      // Auto-save: generation is the costly step, storage is free.
      const id = saveToStorage(data.study_guide, data.study_guide.title);
      setCurrentEntryId(id);
      refreshSaved();
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
    setCurrentEntryId(null);
    setError(null);
  };

  const loadSaved = (savedEntry) => {
    if (savedEntry?.studyGuide) {
      setStudyGuide(savedEntry.studyGuide);
      setCurrentEntryId(savedEntry.id);
      setError(null);
    }
  };

  const deleteSaved = (id) => {
    deleteFromStorage(id);
    if (id === currentEntryId) {
      setStudyGuide(null);
      setCurrentEntryId(null);
    }
    refreshSaved();
  };

  const renameSaved = (id, newName) => {
    updateStudyGuideName(id, newName);
    refreshSaved();
  };

  const currentEntry = savedGuides.find((g) => g.id === currentEntryId) || null;

  return {
    generate,
    studyGuide,
    currentEntry,
    loading,
    error,
    reset,
    savedGuides,
    loadSaved,
    deleteSaved,
    renameSaved,
    refreshSaved,
  };
}

export default useStudyGuide;
