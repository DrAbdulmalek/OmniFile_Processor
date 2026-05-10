import { useState } from 'react';

/**
 * BatchSettings - Configuration panel for batch processing.
 *
 * @param {{ config: object, onSave: function, disabled: boolean }} props
 */
export default function BatchSettings({ config = {}, onSave, disabled = false }) {
  const [form, setForm] = useState({
    ocr_engine: config.ocr_engine || 'trocr',
    language: config.language || 'ar',
    quality: config.quality || 'medium',
    auto_correct: config.auto_correct !== false,
    dpi: config.dpi || 300,
  });

  const handleChange = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = () => {
    onSave && onSave(form);
  };

  return (
    <div className="space-y-4">
      <h3 className="font-bold text-gray-800 text-lg">⚙️ إعدادات المعالجة</h3>

      {/* OCR Engine */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          محرك OCR
        </label>
        <select
          value={form.ocr_engine}
          onChange={(e) => handleChange('ocr_engine', e.target.value)}
          disabled={disabled}
          className="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="trocr">TrOCR (الأفضل لليدوي)</option>
          <option value="easyocr">EasyOCR (متوازن)</option>
          <option value="tesseract">Tesseract (سريع)</option>
          <option value="paddleocr">PaddleOCR (سريع للطباعة)</option>
          <option value="surya">Surya (متقدم)</option>
        </select>
      </div>

      {/* Language */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          اللغة
        </label>
        <select
          value={form.language}
          onChange={(e) => handleChange('language', e.target.value)}
          disabled={disabled}
          className="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
        >
          <option value="ar">عربي</option>
          <option value="en">English</option>
          <option value="multi">مختلط</option>
        </select>
      </div>

      {/* Quality */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          جودة الإخراج
        </label>
        <div className="flex gap-2">
          {[
            { value: 'fast', label: 'سريع' },
            { value: 'medium', label: 'متوسط' },
            { value: 'high', label: 'عالي' },
          ].map((opt) => (
            <button
              key={opt.value}
              onClick={() => handleChange('quality', opt.value)}
              disabled={disabled}
              className={`flex-1 py-2 text-sm rounded-lg transition-colors ${
                form.quality === opt.value
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* DPI */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          DPI: {form.dpi}
        </label>
        <input
          type="range"
          min="150"
          max="600"
          step="50"
          value={form.dpi}
          onChange={(e) => handleChange('dpi', parseInt(e.target.value))}
          disabled={disabled}
          className="w-full accent-blue-600"
        />
        <div className="flex justify-between text-xs text-gray-400">
          <span>150</span>
          <span>300</span>
          <span>600</span>
        </div>
      </div>

      {/* Auto Correct Toggle */}
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-700">التصحيح التلقائي</span>
        <button
          onClick={() => handleChange('auto_correct', !form.auto_correct)}
          disabled={disabled}
          className={`relative w-11 h-6 rounded-full transition-colors ${
            form.auto_correct ? 'bg-blue-600' : 'bg-gray-300'
          }`}
        >
          <span
            className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform ${
              form.auto_correct ? 'left-[22px]' : 'left-0.5'
            }`}
          />
        </button>
      </div>

      {/* Save Button */}
      {onSave && (
        <button
          onClick={handleSave}
          disabled={disabled}
          className="w-full py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
        >
          حفظ الإعدادات
        </button>
      )}
    </div>
  );
}
