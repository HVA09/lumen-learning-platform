# خريطة طلبات الدمج ومسارات التكامل — Lumen

آخر تحقق: **2026-11-04**.
المرجع: المستودع `HVA09/lumen-learning-platform`، والفرع الأساسي `main`.

## 1. الحالة الحالية

- HEAD الحالي لـ `main`: `ee149a40b144883b0fea34232ae730574d5e5ed7` بعد PR #46.
- لا نعدّ أي PR مدمجًا إلا بعد التحقق من حالة GitHub والـ merge commit.
- لا يوجد نشر إنتاجي مثبت.
- [CI #41744744642](https://github.com/HVA09/lumen-learning-platform/actions/runs/41744744642) نجح بالكامل على رأس PR #46.
- [CI #41745646366](https://github.com/HVA09/lumen-learning-platform/actions/runs/41745646366) هو تشغيل `main` بعد دمج PR #46، وكان جاريًا عند آخر تحقق.
- [CI #41738681026](https://github.com/HVA09/lumen-learning-platform/actions/runs/41738681026) نجح على رأس PR #39 بعد إعادة تأسيسه؛ [CI #41744675433](https://github.com/HVA09/lumen-learning-platform/actions/runs/41744675433) نجح على `main` عند commit ما قبل PR #46.

## 2. PRs المدمجة حديثًا

| PR | التغيير | Merge commit | الحالة |
|---|---|---|---|
| #39 | تصحيح متغير فترة النسخ الخارجي في Compose وإضافة regression assertion | `b63574af78f20971563a0a8bc9df2f0a563515a7` | مدمج |
| #40 | فصل Gamification scoring عن ORM/SQL | `2623727c13fa51c7eb1ffb54b2313aa3276ae6dc` | مدمج |
| #41 | Hook لدورة WebSocket للإشعارات | `9481c7927cd06653c584f3b11faa4e1d842259b9` | مدمج |
| #43 | Hook لدورة الجلسة | `9a2a23c071f31f8553b3b1eef9f67195f3b08f07` | مدمج |
| #44 | Hook لحالة الإشعارات والقراءة الآمنة عبر تبدل الجلسة | `aec9584df78009b07c8bed35b48742d7b7a60ede` | مدمج |
| #46 | نقل الإشعارات إلى `features/notifications` | `ee149a40b144883b0fea34232ae730574d5e5ed7` | مدمج؛ CI #41744744642 ناجح |

P5.1–P5.4 دخلت `main` عبر PR #41 ثم #43 ثم #44 ثم #46. دُمجت تغييرات PR #39 بعد إعادة تأسيسها ونجاح CI؛ كما دُمجت PR #42 و#45 للتوثيق وخط أساس الجودة.

## 3. طلبات التوثيق والهيكلة المدمجة مؤخرًا

| PR | المجال | Base | الرأس الحالي | النطاق / CI |
|---|---|---|---|---|
| #42 | خريطة بنية Frontend وخطة Features/Shared | `main` | `e33b6e016339bcc5a50165ccd7238121d7e2202f` | مدمج عبر `aaeeb38e0b16c0ee2d2cea3664a6a3b6b00e1eac`؛ CI #41743356088 ناجح |
| #45 | خط أساس الجودة وخطة P6 وتحديث السجلات | `main` | `56d2fef72dd141bf63babbcdfc0ed8fdecdb9e24` | مدمج عبر `4445ddaf347bf97ae3e89450d7dce01a7bb65eb6`؛ CI #41744217145 ناجح |
| #46 | P5.4 — نقل notifications إلى `features/notifications` | `main` | `959ab53f21f51d76eec02ddab1542333384fec32` | مدمج عبر `ee149a40b144883b0fea34232ae730574d5e5ed7`؛ CI #41744744642 ناجح بجميع الوظائف |

لا تعتمد نتائج CI التاريخية على رؤوس قديمة كبديل عن الفحص على الرأس الحالي.

## 4. سلسلة LTI/AGS — PR #16 إلى #23

هذه السلسلة ما زالت مسودات متراكبة على فروع قديمة، وليست جزءًا من `main`:

| PR | التغيير | Base | Head |
|---|---|---|---|
| #16 | LTI AGS 2.0 grade passback وoutbox | `fix/backup-atomicity-and-restore-guards` | `feat/lti-ags-grade-passback` |
| #17 | واجهة إدارة LTI | `feat/lti-ags-grade-passback` | `feat/lti-admin-console` |
| #18 | upsert متزامن لـ resource-link discovery | `feat/lti-admin-console` | `fix/lti-resource-discovery-upsert` |
| #19 | تقليل قفل DB حول OIDC verification | `fix/lti-resource-discovery-upsert` | `fix/lti-oidc-short-lock` |
| #20 | حدود مدخلات تسجيل المنصة | `fix/lti-oidc-short-lock` | `fix/lti-platform-input-validation` |
| #21 | التحقق من learner profile claims | `fix/lti-platform-input-validation` | `fix/lti-profile-claim-validation` |
| #22 | منع سباقات ربط هوية الطالب | `fix/lti-profile-claim-validation` | `fix/lti-concurrent-identity-link` |
| #23 | اختبارات retry وleases وخصوصية أحداث الدرجات | `fix/lti-concurrent-identity-link` | `test/lti-admin-grade-event-retry` |

### خطة التكامل الآمنة

1. لا تدمج #16–#23 مباشرة إلى main ولا تعتمد على CI تاريخي على رؤوس قديمة.
2. أنشئ فرع تكامل جديدًا من أحدث main بعد إغلاق التوثيق الجاري.
3. أعد تأسيس أو cherry-pick السلسلة بالترتيب من #16 إلى #23 بعد مراجعة commit graph.
4. افحص تعارضات `backend/app/models/lti.py` وrouters وschemas وservices يدويًا؛ لا تستبدل ملفات كاملة.
5. تحقق من ترتيب migration revision IDs واختبر upgrade/downgrade والحفاظ على البيانات على PostgreSQL.
6. شغّل Backend وFrontend وGitleaks وCompose وbackup/restore على رأس التكامل الجديد.
7. اختبر تكاملًا حيًا على Moodle أو Canvas Sandbox قبل أي تفعيل إنتاجي.

## 5. الطلبات القديمة

- PR #1 أرشيفات مصدر أولية؛ لا يدمج فوق خط الأساس الحالي.
- PR #2 استيراد أولي مستبدل بدمج PR #4.
- PR #3 تشديد أمان تاريخي مستبدل؛ لا يدمج دون وجود فرق فريد مثبت.
- PR #5 تهيئة المسؤول الأول: توجد آلية CLI في main؛ قارن أي اختلاف فريد قبل الإغلاق.
- PR #6 وثائق معمارية قديمة؛ لا تعتمد كما هي دون تحديث الوقائع على main الحالي.

## 6. قواعد الدمج

- ابدأ كل تغيير من أحدث SHA على `main`؛ لا تستند إلى فرع متأخر أو متباعد.
- افحص الملفات المتغيرة والـ diff قبل الدمج، وتأكد من scope واضح.
- اشترط CI ناجحًا على رأس PR الحالي، ثم تحقق من CI على main بعد الدمج.
- لا تتجاوز branch protection أو الفحوص الإلزامية أو تزور مراجعة.
- لا تخلط النجاح الآلي مع مراجعة بشرية أو اختبار LMS حي أو نشر إنتاجي.
- حدّث `PROJECT_STATUS.md` و`DECISIONS.md` و`ARCHITECTURE_PLAN.md` بعد التغييرات ذات الصلة.
