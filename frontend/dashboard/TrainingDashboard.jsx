/**
 * TrainingDashboard.jsx - Dashboard for HTR Training Management
 *
 * React component for monitoring and controlling the Arabic HTR
 * training pipeline from the web interface.
 */

import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = '/api/training';

function StatusBadge({ status }) {
  const colors = {
    idle: 'bg-gray-200 text-gray-700',
    running: 'bg-blue-100 text-blue-700',
    completed: 'bg-green-100 text-green-700',
    failed: 'bg-red-100 text-red-700',
    stopped: 'bg-yellow-100 text-yellow-700',
    error: 'bg-red-100 text-red-700',
  };
  return (
    <span className={`px-3 py-1 rounded-full text-sm font-medium ${colors[status] || colors.idle}`}>
      {status}
    </span>
  );
}

function MetricCard({ title, value, unit }) {
  return (
    <div className="bg-white rounded-lg shadow p-4 border border-gray-100">
      <h3 className="text-sm font-medium text-gray-500">{title}</h3>
      <div className="mt-1 flex items-baseline">
        <span className="text-2xl font-bold text-gray-900">{value || 'N/A'}</span>
        {unit && <span className="ml-1 text-sm text-gray-500">{unit}</span>}
      </div>
    </div>
  );
}

function LogViewer({ logs }) {
  const [autoScroll, setAutoScroll] = useState(true);
  useEffect(() => {
    if (autoScroll) {
      const el = document.getElementById('log-container');
      if (el) el.scrollTop = el.scrollHeight;
    }
  }, [logs, autoScroll]);

  return (
    <div className="bg-gray-900 rounded-lg overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 bg-gray-800">
        <span className="text-sm text-gray-300 font-mono">Training Logs</span>
        <button onClick={() => setAutoScroll(!autoScroll)} className="text-xs text-gray-400 hover:text-white">
          {autoScroll ? 'Auto-scroll ON' : 'Auto-scroll OFF'}
        </button>
      </div>
      <div id="log-container" className="h-64 overflow-y-auto p-4 font-mono text-xs">
        {logs.map((log, i) => (
          <div key={i} className="text-green-400 leading-relaxed">{log}</div>
        ))}
        {logs.length === 0 && <div className="text-gray-500">No logs yet...</div>}
      </div>
    </div>
  );
}

export default function TrainingDashboard() {
  const [status, setStatus] = useState(null);
  const [systemInfo, setSystemInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/status`);
      setStatus(await res.json());
    } catch (e) { setError('Failed to fetch status'); }
  }, []);

  const fetchSystemInfo = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/system-info`);
      setSystemInfo(await res.json());
    } catch (e) { setError('Failed to fetch system info'); }
  }, []);

  useEffect(() => {
    fetchStatus();
    fetchSystemInfo();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, [fetchStatus, fetchSystemInfo]);

  const startTraining = async () => {
    setLoading(true); setError(null);
    try {
      const res = await fetch(`${API_BASE}/start`, { method: 'POST' });
      const data = await res.json();
      if (data.status === 'error') setError(data.message);
      setTimeout(fetchStatus, 1000);
    } catch (e) { setError('Failed to start training'); }
    setLoading(false);
  };

  const stopTraining = async () => {
    setLoading(true);
    try {
      await fetch(`${API_BASE}/stop`, { method: 'POST' });
      setTimeout(fetchStatus, 1000);
    } catch (e) { setError('Failed to stop training'); }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-gray-50" dir="rtl">
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">لوحة تحكم التدريب</h1>
            <p className="text-sm text-gray-500 mt-1">نظام تدريب TrOCR مع LoRA للتعرف على خط اليد العربي</p>
          </div>
          <div className="flex items-center gap-3">
            <StatusBadge status={status?.status || 'idle'} />
            <button onClick={startTraining} disabled={status?.status === 'running' || loading}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
              بدء التدريب
            </button>
            <button onClick={stopTraining} disabled={status?.status !== 'running' || loading}
              className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-50">
              إيقاف التدريب
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border-b border-red-200 px-6 py-3">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      <div className="border-b border-gray-200 bg-white px-6">
        <nav className="flex gap-6">
          {[{ id: 'overview', label: 'نظرة عامة' }, { id: 'logs', label: 'السجلات' }, { id: 'system', label: 'معلومات النظام' }]
            .map(tab => (
              <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                className={`py-3 text-sm font-medium border-b-2 ${activeTab === tab.id ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
                {tab.label}
              </button>
            ))}
        </nav>
      </div>

      <div className="p-6">
        {activeTab === 'overview' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <MetricCard title="حالة التدريب" value={status?.status || 'idle'} />
              {systemInfo?.cuda_available && <MetricCard title="بطاقة الرسومات" value={systemInfo.gpu_name} />}
              {systemInfo?.train_samples && <MetricCard title="عينات التدريب" value={systemInfo.train_samples} />}
              {systemInfo?.gpu_memory_gb && <MetricCard title="ذاكرة GPU" value={systemInfo.gpu_memory_gb} unit="GB" />}
            </div>
            <div className="bg-white rounded-lg shadow p-6 border border-gray-100">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">تفاصيل الحالة</h2>
              <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div><dt className="text-sm font-medium text-gray-500">PID</dt><dd className="mt-1 text-sm text-gray-900">{status?.pid || 'N/A'}</dd></div>
                <div><dt className="text-sm font-medium text-gray-500">ملف التكوين</dt><dd className="mt-1 text-sm text-gray-900 font-mono">{status?.config || 'N/A'}</dd></div>
                <div><dt className="text-sm font-medium text-gray-500">عدد سطور السجل</dt><dd className="mt-1 text-sm text-gray-900">{status?.log_count || 0}</dd></div>
              </dl>
            </div>
          </div>
        )}
        {activeTab === 'logs' && <LogViewer logs={status?.recent_logs || []} />}
        {activeTab === 'system' && systemInfo && (
          <div className="bg-white rounded-lg shadow p-6 border border-gray-100">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">معلومات النظام</h2>
            <pre className="text-sm text-gray-700 bg-gray-50 p-4 rounded-lg overflow-x-auto font-mono">
              {JSON.stringify(systemInfo, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
