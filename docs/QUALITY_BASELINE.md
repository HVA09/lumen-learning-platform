# خط أساس الجودة والتحقق — المرحلة P6

آخر تحديث: **2026-11-04**.

## 1. المرجع وحدود هذا التقييم

- المستودع: `HVA09/lumen-learning-platform`.
- خط أساس `main` المحدث بعد دمج PR #53: `4f70cb904e7f92283af8e16a738caf283e5ae494`.
- هذا الملف يوثق ما هو مفعّل فعليًا في المستودع وCI، ثم يقترح إدخال أدوات الجودة تدريجيًا.
- هذا التقييم توثيقي فقط؛ لا يضيف اعتماديات أو يغيّر سلوك التطبيق أو شروط CI.

## 2. ما يفعله CI الآن

ملف `.github/workflows/ci.yml` يشغّل ثلاثة Jobs عند Pull Request والتغييرات على `main`:

| Job | التحقق الحالي |
|---|---|
| Frontend tests and production build | تثبيت الاعتماديات بواسطة `npm ci`، اختبارات Vitest، بناء Vite الإنتاجي، تدقيق الاعتماديات الإنتاجية |
| Backend tests | Python 3.12، Ruff 0.17.3 report-only، PostgreSQL 16 وRedis، اختبار pytest الكامل، migrations، Compose، Restic smoke، وPostgreSQL backup/restore |
| Full Git history secret scan | Gitleaks على نطاق PR، وفحص كل refs والتاريخ الكامل والأرشيفات |

نتيجة خط الأساس المدمج:

- CI #547 على خط الأساس التاريخي `de79d3e4`: Backend **417 passed** مع 20 warning؛ Frontend **51 passed** عبر 11 ملف اختبار.
- بعد دمج P5.1–P5.3، نجح CI على `main` عند commit `aec9584df78009b07c8bed35b48742d7b7a60ede` (run #41738385373).
- بعد PR #49، رأس `main` هو `42986e93060c09e00ffcf917a784390f35adb40f`؛ CI #41754238271 نجح بالكامل بعد الدمج.
- أحدث تحقق كامل لتغييرات P5.3 في PR #44 بعد إعادة تأسيسه على `main`: CI #41737808038 على الرأس `356aad52874ec7086215edd8d892e4894d0c1c4c`؛ وظائف Backend وFrontend/build وGitleaks نجحت.
- في CI #41737808038 نجح Vite production build، وتدقيق الاعتماديات الإنتاجية، وGitleaks، وCompose، وRestic CI smoke، والتحقق من migrations وPostgreSQL backup/restore.
- PR #39 أصلح escaping لمتغيرات shell في خدمة `offsite_backup` وأضاف assertion يتحقق من command بعد Docker Compose rendering؛ CI #41738681026 نجح قبل دمجه إلى `main` في commit `b63574af78f20971563a0a8bc9df2f0a563515a7`.
- PR #46 نقل الإشعارات إلى `features/notifications`؛ كل وظائف CI على رأس PR #46 نجحت في #41744744642، ثم نجحت جميع وظائف CI على `main` بعد الدمج في #41745646366.
- PR #49 أضاف Ruff 0.17.3 كتقرير فقط؛ PR #52 جعل إعادة التصدير المقصودة صريحة، وPR #53 عالج الاستيرادات والتعيينات والمتغيرات المتبقية. CI #41757169187 على PR #53 نجح بالكامل: Backend **423 passed, 20 warnings**، وFrontend **73 passed عبر 14 ملفًا**، production build، Gitleaks، Compose، migrations وbackup/restore.
- تقرير Ruff بعد المعالجة: **0 diagnostic(s)**. لا توجد حتى الآن بوابة lint تمنع الدمج.
- تشغيل main بعد دمج PR #53: [CI #41757735260](https://github.com/HVA09/lumen-learning-platform/actions/runs/41757735260) نجح بالكامل على commit `4f70cb904e7f92283af8e16a738caf283e5ae494`؛ Backend 423 passed و20 warnings، Frontend 73 passed عبر 14 ملفًا، Gitleaks وmigrations وCompose وRestic وPostgreSQL backup/restore نجحت.
- بناء الواجهة في CI #41757169187 أظهر `index-DoXdqRsw.js` بحجم 830.50 kB قبل gzip و258.09 kB بعد gzip، كما ظهر `AdminDashboard` بحجم 401.91 kB قبل gzip؛ ما زال تحذير Vite بشأن حجم chunk قائمًا ولا توجد ميزانية أداء معتمدة.
- تدقيق الاعتماديات الإنتاجية في CI #41757169187: **0 vulnerabilities** عند المستوى الذي يفحصه الأمر الحالي.
- نتيجة npm production audit في CI #570: **0 vulnerabilities** عند مستوى High/Critical المشمول بالأمر الحالي. أما التقرير الكامل لكل شجرة الاعتماديات فسجّل **10 تنبيهات غير عالية: 2 Low و8 Moderate**؛ أغلبها في سلسلة `vite-plugin-pwa` والاعتماديات التابعة لها. لا تُحدّث السلسلة عشوائيًا؛ افحص الشجرة والتوافق وPWA قبل أي ترقية.
- يظهر تحذير حجم Chunk في بناء Vite، ولا يوجد حتى الآن حد أداء رقمي معتمد.

روابط النتائج:
- [CI #547 — خط أساس تاريخي](https://github.com/HVA09/lumen-learning-platform/actions/runs/41689692319)
- [CI #41737808038 — تحقق PR #44 بعد إعادة التأسيس](https://github.com/HVA09/lumen-learning-platform/actions/runs/41737808038)
- [CI #41738385373 — main بعد دمج PR #44](https://github.com/HVA09/lumen-learning-platform/actions/runs/41738385373)
- [CI #41738681026 — PR #39 بعد إعادة التأسيس](https://github.com/HVA09/lumen-learning-platform/actions/runs/41738681026)
- [CI #41742892283 — main بعد دمج PR #39](https://github.com/HVA09/lumen-learning-platform/actions/runs/41742892283)
- [CI #41743356088 — PR #42 قبل الدمج](https://github.com/HVA09/lumen-learning-platform/actions/runs/41743356088)
- [CI #41744012439 — main بعد دمج PR #42](https://github.com/HVA09/lumen-learning-platform/actions/runs/41744012439)
- [CI #41744744642 — PR #46 قبل الدمج](https://github.com/HVA09/lumen-learning-platform/actions/runs/41744744642)
- [CI #41745646366 — main بعد دمج PR #46](https://github.com/HVA09/lumen-learning-platform/actions/runs/41745646366)
- [CI #41750390626 — PR #49 Ruff report-only](https://github.com/HVA09/lumen-learning-platform/actions/runs/41750390626)
- [CI #41754238271 — main بعد دمج Ruff](https://github.com/HVA09/lumen-learning-platform/actions/runs/41754238271)
- [CI #41757735260 — main بعد PR #53 وإغلاق Ruff baseline](https://github.com/HVA09/lumen-learning-platform/actions/runs/41757735260)

مهم: تغييرات P5.1–P5.3 أصبحت جزءًا من `main` بعد دمج PR #41 ثم #43 ثم #44 بالترتيب. نجاح CI لا يثبت تشغيلًا إنتاجيًا أو اختبار متصفح حي.

## 3. الأدوات والقدرات الموجودة في الواجهة

ملف `frontend/package.json` يحتوي scripts التالية فقط:

- `dev`
- `build`
- `preview`
- `test` — يشغّل `vitest run`

الاختبارات تستخدم Vitest وReact Testing Library وjsdom وفق إعداد `frontend/vite.config.js`.

لا يظهر حاليًا script مستقل لـ ESLint أو TypeScript typecheck أو browser end-to-end test في `package.json` أو CI. لا توجد حاليًا خطوة Playwright/Cypress في workflow المعتمد.

## 4. الأدوات والقدرات الموجودة في الخلفية

- Python 3.12 في CI.
- `backend/requirements-dev.txt` يضيف pytest و`ruff==0.17.3` إلى متطلبات التطوير فقط؛ Ruff ليس اعتمادًا تشغيليًا.
- `backend/ruff.toml` يحدد Python 3.12 وطول سطر 100 وقواعد `E4`, `E7`, `E9`, و`F`.
- CI يشغّل `ruff check app tests scripts migrations --output-format=json` بوضع report-only؛ نتيجة Ruff ذات الملاحظات لا تفشل المهمة، لكن أخطاء تشغيل Ruff أو إعداداته (exit code أكبر من 1) تفشلها.
- التحقق الآلي الأساسي لا يزال pytest كاملًا مع PostgreSQL وRedis وخطوات الترحيل والنسخ/الاستعادة.
- لا يوجد mypy أو coverage gate أو ESLint أو TypeScript typecheck.

هذا لا يعني أن الشيفرة خالية من الأخطاء الساكنة؛ يعني فقط أن هذه الأدوات لم تصبح بوابات CI مثبتة حتى الآن.

## 5. فجوات P6 التي نغلقها تدريجيًا

| المجال | الوضع الحالي | الفجوة |
|---|---|---|
| Lint للواجهة | غير مفعّل في scripts/CI | لا يوجد ESLint baseline أو قواعد مشتركة |
| Type checking | لا يوجد TypeScript أو typecheck job | لا يوجد فحص أنواع آلي للواجهة |
| Lint للخلفية | Ruff 0.17.3 report-only | 62 ملاحظة مرصودة؛ لا توجد بوابة منع بعد، ويجب تصنيف compatibility re-exports قبل معالجة F401 |
| تغطية الاختبارات | مجموعات اختبارات ناجحة | لا يوجد coverage baseline أو تقرير اتجاهات |
| Browser E2E | Vitest/jsdom | لا يوجد اختبار متصفح حقيقي لتدفقات الدخول والتعلم والإشعارات |
| الأداء | Vite build مع تحذير chunk | لا توجد ميزانية حجم/زمن مبنية على خط قياس |
| المراقبة | إعدادات تشغيل موجودة جزئيًا | لا يوجد تحقق حي من telemetry على استضافة إنتاجية |

## 6. ترتيب التنفيذ المقترح

### P6.0 — تثبيت خط الأساس

**الحالة: مكتمل توثيقيًا بهذا التقييم.**

نسجل الأدوات الموجودة والفجوات وأرقام CI قبل إضافة شروط جديدة.

### P6.1 — Lint تدريجي دون كسر المستودع

**الحالة: مكتمل للخلفية؛ Ruff report-only baseline الحالي يساوي صفرًا.**

- Ruff مثبت في `backend/requirements-dev.txt` بإصدار `0.17.3`، مع `target-version = py312` و`line-length = 100`.
- مجموعة القواعد: `E4`, `E7`, `E9`, و`F`. يفحص CI مجلدات `app`, `tests`, `scripts`, و`migrations`.
- نتيجة baseline الأولى عبر PR #49: **62 ملاحظة** — `F401`: 49، و`E741`: 10، و`F841`: 3.
- PR #52 جعل إعادة التصدير المقصودة في `achievements.py`, `question_analytics.py`, `quiz_logic.py`, و`streak_logic.py` صريحة باستخدام same-name aliases، مع إبقاء واجهات الاستيراد القديمة واختبارات هوية الرموز.
- PR #53 أزال الاستيرادات غير المستخدمة المؤكدة في LTI، وأزال bindings غير مستخدمة دون إسقاط الآثار الجانبية أو تحقق البيانات، وأعاد تسمية متغيرات الدروس المبهمة في الاختبارات.
- النتيجة بعد PR #53: **0 diagnostic(s)** في Ruff report-only.
- تحقق PR #53: CI #41757169187 نجح بالكامل؛ Backend **423 passed, 20 warnings**، وFrontend **73 passed عبر 14 ملفًا**، وproduction build وتدقيق الإنتاج وGitleaks وCompose وmigrations وPostgreSQL backup/restore وRestic smoke ناجحة.
- لا يستخدم CI `--fix` ولا يحوّل Ruff إلى شرط دمج؛ نجاح Ruff التشغيلي لا يلغي ضرورة إبقاء اختبارات Backend وFrontend والبناء وGitleaks إلزامية.

**الخطوة التالية:**
1. إدخال ESLint للواجهة في وضع report-only بعد مراجعة ملفات إعداد Vite الحالية.
2. تحديث `frontend/package.json` و`frontend/package-lock.json` معًا باستخدام npm، ثم إثبات قابلية إعادة التثبيت عبر `npm ci`.
3. قياس وتصنيف أي findings قبل فرض lint كشرط دمج.
4. لا تضف إعدادات واسعة أو تعطّل قواعد لمجرد إخفاء النتائج.

معيار القبول: لا auto-fix شامل، لا استثناءات واسعة، لا إخفاء للأخطاء، وتظل بوابات الاختبار والأمن الحالية إلزامية.

### P6.2 — Type checking محدود

- ابدأ بوحدات Backend ذات عقود واضحة واختبر أداة الفحص على نطاق صغير.
- لا تحول ملفات React أو Backend إلى TypeScript دفعة واحدة.
- يمكن البدء بتعليقات JSDoc وعقود TypeScript تدريجية للواجهات الحرجة إن أثبت القياس فائدتها.
- لا تجعل التحذيرات القديمة غير المعالجة سببًا لتعطيل التطوير؛ سجّلها ثم شدّد القاعدة تدريجيًا.

### P6.3 — Coverage baseline

- أضف قياس التغطية كتقرير أولًا، لا كحد أدنى اعتباطي.
- ركز على منطق المصادقة والصلاحيات والجلسة، التقييمات، التقدم، الإشعارات، والملفات.
- لا تكتب اختبارات شكلية لرفع النسبة؛ اختبر حالات النجاح والفشل والحدود والتزامن.
- بعد جمع خط أساس موثوق، يمكن وضع حدود صغيرة على الملفات الجديدة أو المتغيرة فقط.

### P6.4 — Browser end-to-end

- اختبر تدفقات رئيسية في متصفح حقيقي: تسجيل الدخول والخروج، استعادة الجلسة، فتح درس وحل اختبار، إشعارات WebSocket، وتبديل RTL/LTR.
- استخدم Playwright أو بديلًا مفتوح المصدر بعد فحص تكامل التشغيل وموارد CI.
- لا تعتمد على حسابات أو بيانات طلاب حقيقية؛ استخدم بيانات اختبار اصطناعية.
- أبقِ هذا الاختبار مستقلًا عن اختبار وحدة Vitest حتى يسهل تشخيص فشل كل طبقة.

### P6.5 — ميزانية الأداء والمراقبة

- سجل مخرجات build وحجم ملفات JS/CSS الحالية قبل اختيار حدود.
- ضع ميزانيات على أساس قياس، لا أرقام تقديرية.
- لا تدّعِ اختبار الأداء الإنتاجي أو observability الحية قبل وجود بيئة تشغيل فعلية.
- حافظ على شرط الميزانية صفر، ولا تضف خدمة مدفوعة أو تتطلب بطاقة.

## 7. بوابات لا يجوز تخفيفها

- Backend tests وFrontend tests/build وGitleaks تظل شروطًا أساسية.
- لا تستخدم `continue-on-error` لإخفاء فشل أمني أو فشل اختبار.
- لا تتجاوز فحص الأسرار، ولا تستثنِ مجلد اختبارات كاملًا.
- لا تضع أسرارًا أو بيانات مستخدمين في الاختبارات أو التقارير.
- لا تغيّر API أو قاعدة البيانات أو صلاحيات المستخدمين ضمن مشروع إعداد أدوات الجودة إلا بقرار منفصل.
- لا تفرض lint/typecheck جديدًا على كل الملفات قبل معرفة baseline وتصنيف النتائج.

## 8. نقطة الاستئناف

1. P6.0 موثق، وP5.4 مكتملة ومدمجة.
2. PR #49 أدخل Ruff؛ PR #52 و#53 أتما معالجة baseline، والنتيجة الحالية **0 diagnostic(s)**. PR #53 CI #41757169187 نجح بجميع وظائفه.
3. Ruff يبقى report-only؛ الخطوة التالية ESLint للواجهة، مع تحديث package.json وpackage-lock.json معًا وتشغيل npm ci قبل اعتماد أي إعداد.
4. أحجام البناء الحالية مسجلة أعلاه؛ يجب قياس أثر أي code splitting لاحقًا قبل وضع ميزانية chunk.
5. لا يوجد نشر إنتاجي مثبت. اختبار Restic الحالي يستخدم مستودعًا مؤقتًا في CI وليس وجهة تخزين خارجية حقيقية.
