import { useMemo } from 'react';

/**
 * StatusCards - Displays batch processing statistics as cards.
 *
 * @param {{ stats: object }} props
 */
export default function StatusCards({ stats }) {
  const cards = useMemo(() => {
    if (!stats) return [];
    return [
      {
        label: 'قيد المعالجة',
        value: stats.processing || 0,
        icon: '⏳',
        color: 'text-yellow-600',
        bg: 'bg-yellow-50',
        border: 'border-yellow-200',
      },
      {
        label: 'مكتمل اليوم',
        value: stats.completed || 0,
        icon: '✅',
        color: 'text-green-600',
        bg: 'bg-green-50',
        border: 'border-green-200',
      },
      {
        label: 'فشل',
        value: stats.failed || 0,
        icon: '❌',
        color: 'text-red-600',
        bg: 'bg-red-50',
        border: 'border-red-200',
      },
      {
        label: 'متوسط الدقة',
        value: stats.avg_confidence
          ? `${(stats.avg_confidence * 100).toFixed(1)}%`
          : '—',
        icon: '📈',
        color: 'text-blue-600',
        bg: 'bg-blue-50',
        border: 'border-blue-200',
      },
    ];
  }, [stats]);

  if (!stats) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="animate-pulse bg-gray-100 rounded-xl p-4 h-24" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card) => (
        <div
          key={card.label}
          className={`${card.bg} ${card.border} border rounded-xl p-4 transition-all hover:shadow-md`}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">{card.label}</p>
              <p className={`text-2xl font-bold mt-1 ${card.color}`}>{card.value}</p>
            </div>
            <span className="text-3xl">{card.icon}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
