import { useState } from "react";
import apiClient from "../api/client";

const ALLOWED_TYPES = [
  "image/jpeg",
  "image/png",
  "image/webp",
  "application/pdf",
  "application/epub+zip",
];

const MAX_SIZE_BYTES = 20 * 1024 * 1024; // 20 MB

/**
 * Validate files before upload.
 * @param {File[]} files
 * @returns {string|null} Error message, or null if valid.
 */
function validateFiles(files) {
  for (const file of files) {
    if (!ALLOWED_TYPES.includes(file.type)) {
      return `"${file.name}" has unsupported type "${file.type}". Accepted: JPEG, PNG, WebP, PDF, EPUB.`;
    }
    if (file.size > MAX_SIZE_BYTES) {
      return `"${file.name}" exceeds the 20 MB size limit.`;
    }
  }
  return null;
}

/**
 * Custom hook for file upload with simulated progress tracking.
 *
 * @returns {{ uploadFiles: Function, loading: boolean, error: string|null, progress: number, reset: Function }}
 */
export function useUpload() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState(0);

  const uploadFiles = async (files) => {
    const fileArray = Array.from(files);
    const validationError = validateFiles(fileArray);
    if (validationError) {
      setError(validationError);
      return null;
    }

    setLoading(true);
    setError(null);
    setProgress(10);

    try {
      // Simulate progress since fetch doesn't support upload progress
      const progressTimer = setInterval(() => {
        setProgress((prev) => (prev < 80 ? prev + 10 : prev));
      }, 300);

      const data = await apiClient.uploadMaterials(fileArray);

      clearInterval(progressTimer);
      setProgress(100);
      return data;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setError(null);
    setProgress(0);
  };

  return { uploadFiles, loading, error, progress, reset };
}

export default useUpload;
