import { useState, useEffect, useCallback } from "react";
import apiClient from "../api/client";
import {
  getQuizHistory,
  saveQuizResult,
  clearQuizHistory as clearHistory,
  deleteHistoryEntry,
} from "../utils/quizHistory";

/**
 * Custom hook for quiz generation, submission, and history tracking.
 *
 * @returns {{
 *   generateQuiz: Function,
 *   submitAnswers: Function,
 *   quiz: object|null,
 *   results: object|null,
 *   loading: boolean,
 *   submitting: boolean,
 *   error: string|null,
 *   reset: Function,
 *   history: Array,
 *   clearHistory: Function,
 *   deleteHistoryItem: Function,
 *   refreshHistory: Function
 * }}
 */
export function useQuiz() {
  const [quiz, setQuiz] = useState(null);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [history, setHistory] = useState([]);

  const refreshHistory = useCallback(() => {
    setHistory(getQuizHistory());
  }, []);

  useEffect(() => {
    refreshHistory();
  }, [refreshHistory]);

  const generateQuiz = async (materialIds, numQuestions, difficulty, questionTypes) => {
    setLoading(true);
    setError(null);
    setResults(null);
    try {
      const data = await apiClient.generateQuiz(
        materialIds,
        numQuestions,
        difficulty,
        questionTypes
      );
      setQuiz(data.quiz);
      return data;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setLoading(false);
    }
  };

  const submitAnswers = async (quizId, answers) => {
    setSubmitting(true);
    setError(null);
    try {
      const data = await apiClient.submitQuiz(quizId, answers);
      setResults(data);

      if (quiz && data.score) {
        saveQuizResult({
          quizId: quiz.id,
          title: quiz.title,
          score: data.score.correct,
          total: data.score.total,
          percentage: data.score.percentage,
        });
        refreshHistory();
      }

      return data;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setSubmitting(false);
    }
  };

  const reset = () => {
    setQuiz(null);
    setResults(null);
    setError(null);
  };

  const handleClearHistory = () => {
    clearHistory();
    refreshHistory();
  };

  const deleteHistoryItem = (id) => {
    deleteHistoryEntry(id);
    refreshHistory();
  };

  return {
    generateQuiz,
    submitAnswers,
    quiz,
    results,
    loading,
    submitting,
    error,
    reset,
    history,
    clearHistory: handleClearHistory,
    deleteHistoryItem,
    refreshHistory,
  };
}

export default useQuiz;
