# 📱 OmniFile Mobile Review v2

تطبيق مراجعة متقدم للتعرف على النصوص اليدوية (HTR).

## المميزات الجديدة

- **واجهة عصرية**: React Native + Expo
- **عمل offline**: تخزين محلي + مزامنة
- **مراجعة ذكية**: اقتراحات AI للتصحيح
- **دعم RTL**: عربي كامل
- **تصحيح سريع**: اختصارات لوحة المفاتيح
- **تعاون فوري**: مراجعة جماعية real-time

## التثبيت

```bash
cd mobile_review_v2
npm install
npx expo start
```

البناء للإنتاج

```bash
# Android
npx expo build:android

# iOS
npx expo build:ios

# Web PWA
npx expo build:web
```

الربط بالخادم

```bash
# الإعدادات
cp .env.example .env

# تحرير .env
API_URL=https://your-server.com/api
WS_URL=wss://your-server.com/ws
```

الاستخدام

1. تسجيل الدخول
2. جلب دفعة مراجعة
3. مراجعة كل صورة
4. إرسال التصحيحات
5. تكرار!
