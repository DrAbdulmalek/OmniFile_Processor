/**
 * GlobalProgress - Overall batch progress bar with stats.
 *
 * @param {{ total: number, completed: number, failed: number }} props
 */
export default function GlobalProgress({ total = 0, completed = 0, failed = 0 }) {
  const processing = total - completed - failed;
  const progress = total > 0 ? Math.round((completed / total) * 100) : 0;

  const segments = [];
  if (completed > 0) segments.push({ pct: (completed / total) * 100, color: 'bg-green-500' });
  if (failed > 0) segments.push({ pct: (failed / total) * 100, color: 'bg-red-500' });
  if (processing > 0) segments.push({ pct: (processing / total) * 100, color: 'bg-yellow-500' });

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="text-gray-600 font-medium">
          التقدم العام
        </span>
        <span className="text-gray-800 font-bold">
          {completed}/{total} ({progress}%)
        </span>
      </div>

      {/* Segmented progress bar */}
      <div className="h-4 bg-gray-100 rounded-full overflow-hidden flex">
        {segments.map((seg, i) => (
          <div
            key={i}
            className={`${seg.color} transition-all duration-500 ease-out`}
            style={{ width: `${seg.pct}%` }}
          />
        ))}
      </div>

      {/* Legend */}
      <div className="flex gap-4 text-xs text-gray-500">
        <span>✅ مكتمل: {completed}</span>
        <span>⏳ قيد المعالجة: {processing}</span>
        <span>❌ فشل: {failed}</span>
      </div>
    </div>
  );
}
