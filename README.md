# Lumen Learning Platform

منصة تعليمية عربية/إنجليزية، بواجهة React + Vite وخلفية FastAPI + PostgreSQL.

## المجلدات

- frontend/: الواجهة الأمامية. راجع frontend/README.md.
- backend/: API والخدمات التعليمية. راجع backend/README.md.

## إعدادات البيئة

راجع frontend/.env.example وbackend/.env.example لإعدادات التطوير. لا ترفع أي ملف بيئة حقيقي أو مفتاح سري. تم استبعاد ملفات .env.production و.env.development من الاستيراد.

## أسلوب العمل

الإصلاحات تُنفّذ في فروع منفصلة وتُراجع عبر Pull Requests. لا تُنشر التغييرات للإنتاج قبل نجاح الاختبارات والتحقق اليدوي.
