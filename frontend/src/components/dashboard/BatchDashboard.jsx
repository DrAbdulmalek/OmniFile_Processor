import { useState, useCallback } from 'react';
import { useWebSocket } from '../../hooks/useWebSocket';
import { batchApi, useBatchManager } from '../../hooks/useBatchManager';
import StatusCards from './StatusCards';
import FileTable from './FileTable';
import GlobalProgress from './GlobalProgress';
import BatchSettings from './BatchSettings';

/**
 * BatchDashboard - Main dashboard component for batch processing.
 *
 * @param {{ batchId: string }} props
 */
export default function BatchDashboard({ batchId }) {
  const { batch, stats, loading, error, refresh } = useBatchManager(batchId);
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);

  // WebSocket for real-time updates
  const wsUrl = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/api/batch/ws/${batchId}`;
  const { isConnected, lastMessage } = useWebSocket(wsUrl);

  // Refresh when WebSocket receives an update
  // (In production, use the WS data directly for instant UI updates)

  // File upload handler
  const handleUpload = useCallback(async (event) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    setUploading(true);
    try {
      await batchApi.uploadFiles(batchId, Array.from(files));
      refresh();
    } catch (e) {
      alert(`فشل الرفع: ${e.message}`);
    } finally {
      setUploading(false);
      event.target.value = '';
    }
  }, [batchId, refresh]);

  // Process handler
  const handleProcess = useCallback(async () => {
    setProcessing(true);
    try {
      await batchApi.process(batchId);
      refresh();
    } catch (e) {
      alert(`فشل التشغيل: ${e.message}`);
    } finally {
      setProcessing(false);
    }
  }, [batchId, refresh]);

  // Retry handler
  const handleRetry = useCallback(async (fileIds) => {
    try {
      await batchApi.retry(batchId);
      refresh();
    } catch (e) {
      alert(`فشل إعادة المعالجة: ${e.message}`);
    }
  }, [batchId, refresh]);

  // Export handler
  const handleExport = useCallback(async (fileId) => {
    try {
      const blob = await batchApi.export(batchId, 'json');
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `batch_${batchId}_results.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert(`فشل التصدير: ${e.message}`);
    }
  }, [batchId]);

  // Config save handler
  const handleConfigSave = useCallback(async (config) => {
    try {
      // Note: would need an update endpoint
      refresh();
    } catch (e) {
      alert(`فشل حفظ الإعدادات: ${e.message}`);
    }
  }, [refresh]);

  if (loading && !batch) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto" />
          <p className="mt-4 text-gray-500">جاري التحميل...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center text-red-500">
          <p className="text-xl font-bold">خطأ</p>
          <p className="mt-2">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6" dir="rtl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">
            📊 لوحة التحكم
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {batch?.name || `دفعة ${batchId}`}
            {isConnected && (
              <span className="text-green-500 mr-2">● متصل</span>
            )}
          </p>
        </div>
        <div className="flex gap-2">
          <label className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 cursor-pointer transition-colors">
            📤 رفع ملفات
            <input
              type="file"
              multiple
              accept=".pdf,.png,.jpg,.jpeg,.bmp,.tiff,.webp"
              onChange={handleUpload}
              disabled={uploading || processing}
              className="hidden"
            />
          </label>
          <button
            onClick={handleProcess}
            disabled={processing || !batch?.files?.length}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
          >
            {processing ? '⏳ جاري المعالجة...' : '🚀 بدء المعالجة'}
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <StatusCards stats={stats} />

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* File Table (3/4 width) */}
        <div className="lg:col-span-3">
          <div className="bg-white rounded-xl border p-4">
            <FileTable
              files={batch?.files || []}
              onRetry={handleRetry}
              onExport={handleExport}
            />
          </div>
        </div>

        {/* Settings Panel (1/4 width) */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-xl border p-4">
            <BatchSettings
              config={batch?.config || {}}
              onSave={handleConfigSave}
              disabled={processing}
            />
          </div>
        </div>
      </div>

      {/* Global Progress */}
      {batch?.files?.length > 0 && (
        <div className="bg-white rounded-xl border p-4">
          <GlobalProgress
            total={stats?.total || 0}
            completed={stats?.completed || 0}
            failed={stats?.failed || 0}
          />
        </div>
      )}
    </div>
  );
}
