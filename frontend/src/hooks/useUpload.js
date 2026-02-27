// import { useState } from "react";
// import apiClient from "../api/client";

/**
 * Custom hook for file upload with progress tracking.
 *
 * Manages upload state (loading, error, progress) and calls
 * the backend upload endpoint.
 *
 * TODO: Implement with:
 * - loading state (boolean)
 * - error state (string or null)
 * - progress state (0-100 percentage)
 * - uploadFiles(files) function that:
 *   1. Sets loading to true
 *   2. Calls apiClient.uploadMaterials(files)
 *   3. Updates progress during upload (if using XMLHttpRequest for progress events)
 *   4. Returns uploaded material metadata
 *   5. Handles errors and sets error state
 *   6. Sets loading to false
 * - reset() function to clear error state
 *
 * @returns {{ uploadFiles: Function, loading: boolean, error: string|null, progress: number }}
 */
export function useUpload() {
  // TODO: Implement upload hook
  // const [loading, setLoading] = useState(false);
  // const [error, setError] = useState(null);
  // const [progress, setProgress] = useState(0);
  //
  // const uploadFiles = async (files) => { ... };
  // const reset = () => { setError(null); setProgress(0); };
  //
  // return { uploadFiles, loading, error, progress, reset };

  throw new Error("useUpload hook not yet implemented");
}

export default useUpload;
