import { useState } from 'react';

/**
 * FileTable - Displays batch files with status, actions, and selection.
 *
 * @param {{ files: Array, onRetry: function, onExport: function }} props
 */
export default function FileTable({ files = [], onRetry, onExport }) {
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [filter, setFilter] = useState('all');

  const filteredFiles = useMemo(() => {
    if (filter === 'all') return files;
    return files.filter((f) => f.status === filter);
  }, [files, filter]);

  const toggleSelect = (fileId) => {
    const next = new Set(selectedIds);
    if (next.has(fileId)) next.delete(fileId);
    else next.add(fileId);
    setSelectedIds(next);
  };

  const toggleAll = () => {
    if (selectedIds.size === filteredFiles.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filteredFiles.map((f) => f.file_id)));
    }
  };

  const statusBadge = (status) => {
    const map = {
      pending: { bg: 'bg-gray-100 text-gray-700', label: 'بانتظار' },
      processing: { bg: 'bg-yellow-100 text-yellow-800', label: 'قيد المعالجة' },
      completed: { bg: 'bg-green-100 text-green-800', label: 'مكتمل' },
      failed: { bg: 'bg-red-100 text-red-800', label: 'فشل' },
      retrying: { bg: 'bg-orange-100 text-orange-800', label: 'إعادة المحاولة' },
    };
    const s = map[status] || map.pending;
    return <span className={`${s.bg} text-xs font-medium px-2 py-0.5 rounded-full`}>{s.label}</span>;
  };

  const formatTime = (seconds) => {
    if (!seconds) return '—';
    return seconds < 1 ? `${Math.round(seconds * 1000)}ms` : `${seconds.toFixed(1)}s`;
  };

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex gap-1">
          {['all', 'pending', 'processing', 'completed', 'failed'].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1 text-sm rounded-lg transition-colors ${
                filter === f
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {f === 'all' ? 'الكل' :
               f === 'pending' ? 'بانتظار' :
               f === 'processing' ? 'قيد المعالجة' :
               f === 'completed' ? 'مكتمل' : 'فشل'}
            </button>
          ))}
        </div>

        {selectedIds.size > 0 && (
          <div className="flex gap-2 mr-auto">
            <button
              onClick={() => onRetry && onRetry([...selectedIds])}
              className="px-3 py-1.5 text-sm bg-orange-100 text-orange-700 rounded-lg hover:bg-orange-200"
            >
              إعادة معالجة ({selectedIds.size})
            </button>
            <button
              onClick={() => setSelectedIds(new Set())}
              className="px-3 py-1.5 text-sm bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200"
            >
              إلغاء التحديد
            </button>
          </div>
        )}
      </div>

      {/* Table */}
      <div className="border rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="p-3 text-right w-10">
                <input
                  type="checkbox"
                  checked={selectedIds.size === filteredFiles.length && filteredFiles.length > 0}
                  onChange={toggleAll}
                  className="rounded"
                />
              </th>
              <th className="p-3 text-right font-medium text-gray-600">الملف</th>
              <th className="p-3 text-right font-medium text-gray-600">الحالة</th>
              <th className="p-3 text-right font-medium text-gray-600">الدقة</th>
              <th className="p-3 text-right font-medium text-gray-600">الوقت</th>
              <th className="p-3 text-right font-medium text-gray-600">إجراءات</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {filteredFiles.length === 0 ? (
              <tr>
                <td colSpan={6} className="p-8 text-center text-gray-400">
                  لا توجد ملفات
                </td>
              </tr>
            ) : (
              filteredFiles.map((file) => (
                <tr
                  key={file.file_id}
                  className={`hover:bg-gray-50 transition-colors ${
                    selectedIds.has(file.file_id) ? 'bg-blue-50' : ''
                  }`}
                >
                  <td className="p-3">
                    <input
                      type="checkbox"
                      checked={selectedIds.has(file.file_id)}
                      onChange={() => toggleSelect(file.file_id)}
                      className="rounded"
                    />
                  </td>
                  <td className="p-3">
                    <p className="font-medium text-gray-800 truncate max-w-[200px]">
                      {file.filename}
                    </p>
                    {file.error && (
                      <p className="text-xs text-red-500 mt-0.5 truncate max-w-[300px]">
                        {file.error}
                      </p>
                    )}
                  </td>
                  <td className="p-3">{statusBadge(file.status)}</td>
                  <td className="p-3 text-gray-600">
                    {file.confidence ? `${(file.confidence * 100).toFixed(1)}%` : '—'}
                  </td>
                  <td className="p-3 text-gray-500">{formatTime(file.processing_time)}</td>
                  <td className="p-3">
                    <div className="flex gap-1">
                      {file.status === 'failed' && onRetry && (
                        <button
                          onClick={() => onRetry([file.file_id])}
                          className="p-1.5 text-orange-500 hover:bg-orange-50 rounded-lg"
                          title="إعادة المحاولة"
                        >
                          🔄
                        </button>
                      )}
                      {file.status === 'completed' && onExport && (
                        <button
                          onClick={() => onExport(file.file_id)}
                          className="p-1.5 text-blue-500 hover:bg-blue-50 rounded-lg"
                          title="تصدير"
                        >
                          📥
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div className="text-sm text-gray-500 text-center">
        {filteredFiles.length} ملف من أصل {files.length}
        {selectedIds.size > 0 && ` | ${selectedIds.size} محدد`}
      </div>
    </div>
  );
}

function useMemo(fn, deps) {
  // Simple useMemo fallback
  return fn();
}
