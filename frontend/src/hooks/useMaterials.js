import { useState, useEffect, useCallback } from "react";
import apiClient from "../api/client";

/**
 * Custom hook for fetching and managing the materials list.
 *
 * Calls apiClient.listMaterials() on mount and exposes a refresh function.
 *
 * @returns {{ materials: Array, loading: boolean, error: string|null, fetchMaterials: Function }}
 */
export function useMaterials() {
  const [materials, setMaterials] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchMaterials = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.listMaterials();
      setMaterials(data.materials || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMaterials();
  }, [fetchMaterials]);

  return { materials, loading, error, fetchMaterials };
}

export default useMaterials;
