# Lumen Learning Platform

منصة تعليمية عربية/إنجليزية، بواجهة React + Vite وخلفية FastAPI + PostgreSQL.

## المجلدات

- frontend/: الواجهة الأمامية. راجع frontend/README.md.
- backend/: API والخدمات التعليمية. راجع backend/README.md.

## إعدادات البيئة

راجع frontend/.env.example وbackend/.env.example لإعدادات التطوير. لا ترفع أي ملف بيئة حقيقي أو مفتاح سري. تم استبعاد ملفات .env.production و.env.development من الاستيراد.

## أسلوب العمل

الإصلاحات تُنفّذ في فروع منفصلة وتُراجع عبر Pull Requests. لا تُنشر التغييرات للإنتاج قبل نجاح الاختبارات والتحقق اليدوي.


## وثائق المشروع

- [ميثاق المشروع والقيود](docs/PROJECT_CHARTER.md)
- [سجل القرارات الهندسية](docs/DECISIONS.md)
- [الحالة التنفيذية والمهام المتبقية](docs/PROJECT_STATUS.md)
- [استمرارية العمل عبر الأجهزة والمحادثات](docs/CONTINUITY.md)

ابدأ بقراءة `docs/PROJECT_STATUS.md` ثم `docs/DECISIONS.md` قبل استكمال أي مرحلة تطوير.

- [تقييم الاستضافة المجانية والقيود](docs/HOSTING_FEASIBILITY.md)

- [خريطة طلبات الدمج ومسارات LTI المتبقية](docs/PR_STACK_TRIAGE.md)

- [الخطة المعمارية الحالية ومراحل التنظيم](docs/ARCHITECTURE_PLAN.md)
