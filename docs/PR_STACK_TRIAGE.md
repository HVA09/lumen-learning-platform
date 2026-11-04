# خريطة طلبات الدمج ومسارات التكامل — Lumen

آخر تحقق: **2026-11-04**.
المرجع: المستودع `HVA09/lumen-learning-platform`، والفرع الأساسي `main`.

## 1. الحالة الحالية

- HEAD الحالي المتحقق لـ `main`: `96fff938fa5ec85b921de247bfe7a3dbe3300071` بعد دمج PR #57.
- لا نعدّ أي PR مدمجًا إلا بعد التحقق من حالة GitHub والـ merge commit.
- [CI #41745646366](https://github.com/HVA09/lumen-learning-platform/actions/runs/41745646366) نجح بالكامل على `main` بعد PR #46.
- [CI #41754238271](https://github.com/HVA09/lumen-learning-platform/actions/runs/41754238271) نجح بالكامل على `main` بعد PR #49.
- CI [#41757735260](https://github.com/HVA09/lumen-learning-platform/actions/runs/41757735260) نجح بالكامل على `main` بعد PR #53؛ Backend 423 passed و20 warnings، وFrontend 73 passed عبر 14 ملفًا، وGitleaks وbuild وmigrations وbackup/restore وRuff 0 diagnostics كلها ناجحة.
- CI [#41759458975](https://github.com/HVA09/lumen-learning-platform/actions/runs/41759458975) نجح بالكامل على `main` بعد PR #54؛ Backend 423 passed و20 warnings، Ruff 0 diagnostics، Frontend tests/build وGitleaks وmigrations وCompose وRestic وPostgreSQL backup/restore ناجحة.
- PR #56 دُمج في `main` عند `dc2f2267851837e724b015d9d4b8a710fd3b29cf` بعد نجاح PR CI #41760360217؛ CI بعد الدمج #41763352189 نجح بالكامل.
- PR #57 دُمج توثيقيًا عند `96fff938fa5ec85b921de247bfe7a3dbe3300071`؛ PR CI #41766914355 وmain CI #41767787126 نجحا بالكامل.
- [CI #41750390626](https://github.com/HVA09/lumen-learning-platform/actions/runs/41750390626) نجح على PR #49 قبل دمجه.
- لا يوجد نشر إنتاجي مثبت.

## 2. PRs المدمجة حديثًا

| PR | التغيير | Merge commit | الحالة |
|---|---|---|---|
| #39 | تصحيح متغير فترة النسخ الخارجي في Compose وإضافة regression assertion | `b63574af78f20971563a0a8bc9df2f0a563515a7` | مدمج |
| #40 | فصل Gamification scoring عن ORM/SQL | `2623727c13fa51c7eb1ffb54b2313aa3276ae6dc` | مدمج |
| #41 | Hook لدورة WebSocket للإشعارات | `9481c7927cd06653c584f3b11faa4e1d842259b9` | مدمج |
| #43 | Hook لدورة الجلسة | `9a2a23c071f31f8553b3b1eef9f67195f3b08f07` | مدمج |
| #44 | Hook لحالة الإشعارات والقراءة الآمنة عبر تبدل الجلسة | `aec9584df78009b07c8bed35b48742d7b7a60ede` | مدمج |
| #45 | خط أساس الجودة وتحديث سجلات الحالة والقرارات | `4445ddaf347bf97ae3e89450d7dce01a7bb65eb6` | مدمج |
| #46 | نقل الإشعارات إلى `features/notifications` | `ee149a40b144883b0fea34232ae730574d5e5ed7` | مدمج |
| #48 | تحديث نقطة الاستئناف بعد P5.4 | `462dcc3c0386afc42ead51225ccf7c3d28ca21f9` | مدمج |
| #49 | إضافة Ruff report-only baseline | `42986e93060c09e00ffcf917a784390f35adb40f` | مدمج؛ CI #41750390626 و#41754238271 ناجحان |
| #51 | تحديث الحالة والخطة وسجل الجودة بعد Ruff | `f8c3e9653028cc169c95c8dedcc23c364a315e4f` | مدمج؛ PR CI #41755785196 وmain CI #41756353787 ناجحان |
| #52 | جعل إعادة التصدير في واجهات التوافق صريحة | `9b04b4e2154192a0214fe1b5024ae3cdf3dac792` | مدمج؛ PR CI #41756512842 وmain CI #41756990109 ناجحان |
| #53 | معالجة ملاحظات Ruff المتبقية والوصول إلى صفر findings | `4f70cb904e7f92283af8e16a738caf283e5ae494` | مدمج؛ PR CI #41757169187 ناجح: Backend 423 passed وFrontend 73 passed، وRuff 0 diagnostics |
| #54 | تحديث الحالة والخطة وخط أساس الجودة وسجل القرارات | `7f6953636241997156e478a5ec489159825a7d2f` | مدمج؛ CI PR #41758397435 وmain #41759458975 ناجحان |
| #56 | تنظيف 3 findings مؤكدة في واجهة Frontend دون تغيير السلوك | `dc2f2267851837e724b015d9d4b8a710fd3b29cf` | مدمج؛ PR CI #41760360217 وmain CI #41763352189 نجحا |
| #57 | مزامنة الحالة وخط أساس الجودة وتوثيق ESLint blocker | `96fff938fa5ec85b921de247bfe7a3dbe3300071` | مدمج؛ PR CI #41766914355 وmain CI #41767787126 ناجحان |

P5.1–P5.4 دخلت `main`: WebSocket (#41)، Session (#43)، notification state (#44)، ثم نقل notifications (#46). PR #39 أصلح Compose، و#42 و#45 و#48 وثّقت مراحل الواجهة والجودة، و#49 أدخل Ruff، و#51 حدّث السجلات، و#52 صرّح بإعادة التصدير المتوافقة، و#53 خفّض Ruff baseline إلى صفر. PR #55 أُغلق دون دمج؛ كان تقرير npx التجريبي جزئيًا، ولا يُعد baseline رسميًا. PR #56 دمج الإصلاحات المؤكدة التي ظهرت بالتجربة.

## 3. طلبات التوثيق والهيكلة المدمجة

| PR | المجال | Merge commit | الحالة / الدليل |
|---|---|---|---|
| #42 | خريطة بنية Frontend وخطة Features/Shared | `aaeeb38e0b16c0ee2d2cea3664a6a3b6b00e1eac` | مدمج؛ CI #41743356088 ناجح |
| #45 | خط أساس الجودة وخطة P6 وتحديث السجلات | `4445ddaf347bf97ae3e89450d7dce01a7bb65eb6` | مدمج؛ CI على `main` #41744675433 ناجح |
| #46 | P5.4 نقل Notifications إلى `features/notifications` | `ee149a40b144883b0fea34232ae730574d5e5ed7` | مدمج؛ PR CI #41744744642 وmain CI #41745646366 ناجحان |
| #48 | تحديث نقطة الاستئناف بعد PR #46 | `462dcc3c0386afc42ead51225ccf7c3d28ca21f9` | مدمج؛ main CI #41750270590 ناجح |
| #49 | تثبيت Ruff report-only baseline | `42986e93060c09e00ffcf917a784390f35adb40f` | مدمج؛ PR CI #41750390626 وmain CI #41754238271 ناجحان |
| #51 | تحديث سجلات المشروع بعد baseline | `f8c3e9653028cc169c95c8dedcc23c364a315e4f` | مدمج؛ PR/main CI ناجحان |
| #52–#53 | إغلاق Ruff baseline من 62 إلى 0 diagnostics | `9b04b4e2154192a0214fe1b5024ae3cdf3dac792` / `4f70cb904e7f92283af8e16a738caf283e5ae494` | مدمج؛ فحوص PR وmain ناجحة |
| #54 | مزامنة سجل الحالة وخطة الجودة بعد إغلاق Ruff | `7f6953636241997156e478a5ec489159825a7d2f` | مدمج؛ CI #41759458975 ناجح |

أُغلق PR #50 دون دمج؛ كان يكرر تغيير Ruff الذي وصل إلى `main` عبر PR #49. أُغلقت دفعتا Ruff عبر PR #52 و#53 وأصبح baseline صفرًا. أُغلق PR #55 دون دمج كتجربة ESLint مؤقتة (CI #41759875976) وأُزيلت الحالات المؤكدة في PR #56. PR #57 حدّث السجلات وتحقق من CI بعد الدمج. لا يوجد baseline ESLint رسمي؛ لا يمكن توليده في بيئة التنفيذ الحالية بسبب عدم الوصول إلى npm registry وعدم وجود حزم في cache. سلسلة LTI #16–#23 ما زالت منفصلة ومتراكبة على فروع قديمة.

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
