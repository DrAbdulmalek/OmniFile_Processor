import { useState, useEffect, useMemo } from 'react';

/**
 * API helper for OmniFile Batch Manager.
 */
const API_BASE = import.meta.env.VITE_API_BASE || '/api';

async function api(method, path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : null,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'API Error');
  }
  if (res.headers.get('content-type')?.includes('application/json')) {
    return res.json();
  }
  return res.blob();
}

export const batchApi = {
  /** Create a new batch */
  create: (name, config = {}, createdBy = 'anonymous') =>
    api('POST', '/batch', { name, config, created_by: createdBy }),

  /** List all batches */
  list: (status) => {
    const q = status ? `?status=${status}` : '';
    return api('GET', `/batch${q}`);
  },

  /** Get batch details */
  get: (batchId) => api('GET', `/batch/${batchId}`),

  /** Delete a batch */
  delete: (batchId) => api('DELETE', `/batch/${batchId}`),

  /** Upload files to a batch */
  uploadFiles: async (batchId, files) => {
    const formData = new FormData();
    files.forEach((f) => formData.append('files', f));
    const res = await fetch(`${API_BASE}/batch/${batchId}/files`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) throw new Error('Upload failed');
    return res.json();
  },

  /** Start processing a batch */
  process: (batchId) => api('POST', `/batch/${batchId}/process`),

  /** Retry failed files */
  retry: (batchId) => api('POST', `/batch/${batchId}/retry`),

  /** Export results */
  export: (batchId, format = 'json') =>
    api('GET', `/batch/${batchId}/export?format=${format}`),
};

/**
 * useBatchManager - React hook for batch operations.
 */
export function useBatchManager(batchId) {
  const [batch, setBatch] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const refresh = async () => {
    if (!batchId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await batchApi.get(batchId);
      setBatch(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    // Auto-refresh every 5 seconds during processing
    if (batch?.status === 'processing') {
      const interval = setInterval(refresh, 5000);
      return () => clearInterval(interval);
    }
  }, [batchId, batch?.status]);

  const stats = useMemo(() => {
    if (!batch?.stats) return null;
    return batch.stats;
  }, [batch?.stats]);

  return { batch, stats, loading, error, refresh };
}
