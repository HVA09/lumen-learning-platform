# خط أساس الجودة والتحقق — المرحلة P6

آخر تحديث: **2026-11-06**.

## 1. المرجع وحدود هذا التقييم

- المستودع: `HVA09/lumen-learning-platform`.
- آخر تغيير اختبار/جودة مدمج على `main`: PR #119 عند `f1d5884b8ee0a4c05a1be596502a969018bfcbe0`؛ دمج V8 coverage report-only مع 142 اختبار Frontend / 24 ملفًا. أحدث CI Backend baseline: 480 passed، 21 warnings، 90% coverage عبر PR #117/#119. لم تُفرض عتبة تغطية.
- هذا الملف يوثق ما هو مفعّل فعليًا في المستودع وCI، ثم يقترح إدخال أدوات الجودة تدريجيًا.
- هذا التقييم توثيقي فقط؛ لا يضيف اعتماديات أو يغيّر سلوك التطبيق أو شروط CI.

## 2. ما يفعله CI الآن

ملف `.github/workflows/ci.yml` يشغّل أربعة Jobs عند Pull Request والتغييرات على `main`:

| Job | التحقق الحالي |
|---|---|
| Frontend tests and production build | تثبيت الاعتماديات بواسطة `npm ci`، اختبارات Vitest، بناء Vite الإنتاجي، تدقيق الاعتماديات الإنتاجية |
| Backend tests | Python 3.12، Ruff 0.17.3 report-only، PostgreSQL 16 وRedis، اختبار pytest الكامل (بما فيه اختبار حد بوابة Quiz من PR #89)، migrations، Compose، Restic smoke، وPostgreSQL backup/restore |
| Full Git history secret scan | Gitleaks على نطاق PR، وفحص كل refs والتاريخ الكامل والأرشيفات |
| Browser E2E (registration and browser session) | Playwright + Chromium على Vite production preview مع FastAPI وPostgreSQL وRedis وClamAV مؤقتة؛ التسجيل والجلسة، الدرس والتقدم والنشر، Quiz وسجل المحاولات والعتبة، صلاحيات الأدوار وعزل الفصول، إدارة السؤال، وفحص ClamAV الحقيقي. يغطي الاختبار الآن حالة بوابة ناجحة عند الحد، وحالة رسوب أسفل الحد مع حفظ المحاولة وHTTP 429 عند إعادة المحاولة مباشرةً (PR #88، CI 4/4). ويؤكد اختبار Backend المستقل في PR #89 عدم فتح الموضوع التابع عند 70% (CI 4/4). |

نتيجة التحقق لـ P6.6:

- PR #84 وCI [#41953273414](https://github.com/HVA09/lumen-learning-platform/actions/runs/41953273414): أضافا ClamAV 1.4.6 كخدمة مؤقتة في Browser E2E CI. نجح الملف النظيف، ورُفضت عينة EICAR غير الضارة للاختبار بـ HTTP 422؛ تحقق السيناريو من بقاء الملف النظيف فقط وعدم إنشاء سجل attachment للعينة المرفوضة. نجحت وظائف Frontend tests/build وBackend وGitleaks كذلك؛ التشغيل 4/4.
- PR #70 (CI ما بعد الدمج #41914599965) أثبت التسجيل والجلسة الآمنة واستعادتها والخروج.
- PR #73 (CI #41919944969 على رأس `1f929c6403a59cc4154999f42d4c9f784124b963`) وسّع السيناريو إلى إكمال درس والتحقق من حفظ التقدم في الخادم واستعادته بعد reload. الوظائف الأربع نجحت: Backend **423 passed, 20 warnings**؛ Ruff **0 diagnostic(s)**؛ Frontend **80 passed عبر 16 ملفًا**؛ Browser E2E passed؛ production audit **0 vulnerabilities**؛ full dependency audit **2 Low و4 Moderate، وصفر High/Critical**؛ Gitleaks full-history نجح.
- CI ما بعد دمج PR #73 على `main` هو [#41920779594](https://github.com/HVA09/lumen-learning-platform/actions/runs/41920779594) ونجح بجميع الوظائف الأربع على commit `2d8721efbd581952cb16c3b6d64904a6ef5f6256`. Backend **423 passed, 20 warnings**؛ Frontend **80 passed عبر 16 ملفًا**؛ Browser E2E أثبت إكمال الدرس واستمرار التقدم بعد reload؛ Ruff **0 diagnostics**؛ production audit **0 vulnerabilities**؛ full dependency audit **2 Low و4 Moderate**؛ Gitleaks full-history نجح.
- PR #75 وCI [#41925605855](https://github.com/HVA09/lumen-learning-platform/actions/runs/41925605855): أضافا رحلة Quiz حقيقية في المتصفح؛ بدء المحاولة لا يكشف مفاتيح الإجابة، والتسليم الفارغ ينتج الدرجة صفرًا وتغذية راجعة من الخادم، ثم يظهر نفس attempt في سجل المحاولات بعد إعادة التحميل. الوظائف الأربع نجحت.
- CI بعد دمج PR #75 على `main`: [#41938791393](https://github.com/HVA09/lumen-learning-platform/actions/runs/41938791393) نجح على `1c94e4f73695b675d8929daf25b35c8d718aac5d` بالوظائف الأربع. Backend **423 passed, 20 warnings**؛ Frontend **80 passed عبر 16 ملفًا**؛ Ruff **0 diagnostics**؛ production audit **0 vulnerabilities**؛ full dependency audit **2 Low و4 Moderate وصفر High/Critical**؛ Browser E2E وGitleaks full-history نجحا.
- PR #77 وCI [#41940578786](https://github.com/HVA09/lumen-learning-platform/actions/runs/41940578786): نجحت الوظائف الأربع. Browser E2E أنشأ حسابات مؤقتة للمعلمَين والمسؤول، وفحص إخفاء عناصر الإدارة من الطالب، وصول المعلم إلى Content Manager وإنشاء فصل، عزل قوائم الفصول، ومنع قراءة الفصل الآخر برمز 403، ثم التحقق من وصول المسؤول المصرح.
- PR #80 وCI #41943697271: اختبار واجهة المعلم لإنشاء درس كمسودة، والتحقق من عدم ظهوره للطالب، ثم نشره والتحقق من ظهوره في منهج الطالب. CI بعد الدمج #41947786739 نجح 4/4.
- PR #81 وCI #41948823950: اختبار تصحيح Quiz من الخادم بإجابات صحيحة تحقق عتبة اجتياز البوابة. CI بعد الدمج #41949251573 نجح 4/4.
- PR #82 وCI #41949826358: اختبار إنشاء سؤال اختيار متعدد من Content Manager، والتحقق من استجابة المعلم المصرح بها، وتعديل السؤال وتعطيله ثم حذفه والتحقق من غيابه. الوظائف الأربع نجحت. CI بعد الدمج #41950657568 على commit cf15149abe546627ee36feba65fcf48dbab3ba64 نجح 4/4: Backend 423 passed و20 warnings؛ Ruff 0 diagnostics؛ Frontend 80 passed عبر 16 ملفًا؛ production audit 0 vulnerabilities؛ full dependency audit 2 Low و4 Moderate وصفر High/Critical؛ Browser E2E وGitleaks وmigrations وPostgreSQL backup/restore نجحت.
- CI بعد دمج PR #77 على `main`: [#41941142454](https://github.com/HVA09/lumen-learning-platform/actions/runs/41941142454) نجح على `451572c1253351e0b4406ed21480b659b2862406` في الوظائف الأربع (Backend، Frontend/build، Browser E2E، Gitleaks).

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
- PR #54 تحديث توثيقي فقط لخمس وثائق. تشغيل main بعد دمجه: [CI #41759458975](https://github.com/HVA09/lumen-learning-platform/actions/runs/41759458975) نجح بالكامل على `7f6953636241997156e478a5ec489159825a7d2f`؛ Backend **423 passed, 20 warnings**، Ruff **0 diagnostics**، Frontend tests وproduction build وGitleaks وmigrations وCompose وRestic وPostgreSQL backup/restore نجحت. npm production audit وجد **0 vulnerabilities** ضمن مستوى `--audit-level=high` مع `--omit=dev`.
- PR #55 (مغلق دون دمج): تجربة ESLint مؤقتة باستخدام npx على 70 ملف JS/JSX. CI #41759875976 نجح بجميع وظائفه، لكن التقرير لم يكن baseline معتمدًا: 3 تحذيرات `no-unused-vars` (استيراد واحد ومعاملان في `drawCircuit`)، وتوجيها `react-hooks/exhaustive-deps` غير معروفين لأن إضافة React Hooks لم تكن محمّلة، وتعليق تعطيل قديم واحد. لا تعتمد النتائج بوصفها تغطية كاملة لقواعد React.
- PR #56 أزال الحالات الثلاث المؤكدة (استيراد App غير المستخدم، معاملا الرسم غير المستخدمين، وتعليق التعطيل القديم)؛ PR CI #41760360217 وmain CI #41763352189 نجحا.
- PR #57 حدّث السجلات بعد PR #54/#56، ودُمج عبر `96fff938fa5ec85b921de247bfe7a3dbe3300071`؛ CI PR #41766914355 وmain #41767787126 نجحا.
- PR #58 تحديث توثيقي فقط؛ CI بعد دمجه #41850447579 نجح.
- PR #59 نقل `TopicPanel` إلى تحميل React.lazy عند اختيار موضوع؛ CI PR #41850891816 وmain CI #41851527075 نجحا بالكامل: Backend **423 passed, 20 warnings**، Ruff **0 diagnostics**، Frontend **73 passed عبر 14 ملفًا**، production build، Gitleaks، migrations، Compose، Restic وPostgreSQL backup/restore.
- PR #62 (تحميل MathText وKaTeX عند الحاجة) دُمج عند `6b53686ae3824d020243dd33115cc0bf81bd3c03`؛ PR CI [#41855423230](https://github.com/HVA09/lumen-learning-platform/actions/runs/41855423230) وmain CI بعد الدمج [#41856247148](https://github.com/HVA09/lumen-learning-platform/actions/runs/41856247148) نجحا بالكامل: Backend **423 passed, 20 warnings**، Ruff **0 diagnostics**، Frontend **73 passed عبر 14 ملفًا**، production build وGitleaks وفحوص PostgreSQL/backup/restore ناجحة.
- PR #64 (تحميل الاختبارات والمختبر والمحاكاة عند الطلب) دُمج عند `09d2a706236b4f9be55f3d8c66d461fee34f70c1`؛ PR CI [#41857581931](https://github.com/HVA09/lumen-learning-platform/actions/runs/41857581931) وmain CI بعد الدمج [#41858290575](https://github.com/HVA09/lumen-learning-platform/actions/runs/41858290575) نجحا بالكامل: Backend **423 passed, 20 warnings**، Ruff **0 diagnostics**، Frontend **74 passed عبر 14 ملفًا**، production build وGitleaks وmigrations وPostgreSQL backup/restore ناجحة.
- PR #65 (استعادة أخطاء تحميل الوحدات المؤجلة) دُمج عند `ee74aaa1136c471fb4b22b61247528e1ad7478c3`؛ PR CI [#41860852718](https://github.com/HVA09/lumen-learning-platform/actions/runs/41860852718) نجح بالكامل: Backend **423 passed, 20 warnings**، Ruff **0 diagnostics**، Frontend **80 passed عبر 16 ملفًا**، production build وGitleaks ناجحان. CI بعد الدمج على main [#41861598602](https://github.com/HVA09/lumen-learning-platform/actions/runs/41861598602) نجح بالكامل: Backend **423 passed, 20 warnings**، Ruff **0 diagnostics**، Frontend **80 passed عبر 16 ملفًا**، production build وGitleaks وmigrations وPostgreSQL backup/restore ناجحة.
- خط القياس قبل PR #59 في main CI #41767787126: `index-BJz-0WwU.js` **830.50 kB** قبل gzip و**258.06 kB** بعد gzip؛ `AdminDashboard` **401.91 kB** / **110.80 kB gzip**. كان تحذير Vite >500 kB ظاهرًا على entry.
- بعد PR #59 في build ضمن CI #41850891816، وتأكد نفس القياس في main CI #41851527075: `index-CuMtssyR.js` **362.86 kB** / **116.80 kB gzip**؛ `TopicPanel` **23.28 kB** / **6.90 kB gzip**؛ `MathText` **442.53 kB** / **133.49 kB gzip**؛ `AdminDashboard` **401.91 kB** / **110.80 kB gzip**. انخفض entry الأولي بنحو **56.3%** (minified) و**54.7%** (gzip). لم يظهر تحذير Vite لتجاوز chunk حد 500 kB في هذا البناء. هذا قياس build، وليس قياس RUM أو تجربة مستخدم فعلية.
- بعد PR #62 في main CI #41856247148: entry `index-TNoNppgD.js` **362.87 kB / 116.81 kB gzip**؛ wrapper `MathText` **0.70 kB / 0.41 kB gzip**؛ renderer المؤجل `MathTextRenderer` **442.53 kB / 133.49 kB gzip**؛ CSS المؤجل **30.20 kB / 8.08 kB gzip**؛ `TopicPanel` **23.28 kB / 6.91 kB gzip**؛ و`AdminDashboard` **401.91 kB / 110.79 kB gzip**. لا يظهر تحذير Vite >500 kB. الـ renderer وCSS لا يدخلان في التنزيل الأولي، لكنهما يُنزّلان عندما يظهر MathText فعليًا.
- بعد PR #64 في main CI #41858290575: entry `index-BM88lNV5.js` **362.89 kB / 116.82 kB gzip**؛ `TopicPanel` **6.76 kB / 2.47 kB gzip**؛ `QuizPanel` **4.88 kB / 1.96 kB gzip**؛ `LabPanel` **1.80 kB / 0.86 kB gzip**. ملفات المحاكاة المؤجلة: LinearFunctionSim **1.92 / 1.05**، DerivativeSim **1.82 / 1.04**، ProjectileSim **2.47 / 1.29**، PythonLabSim **2.71 / 1.44**، CircuitSim **3.23 / 1.34** kB/gzip. بقي MathTextRenderer **442.53 / 133.49 kB gzip** وAdminDashboard **401.91 / 110.80 kB gzip** كملفات منفصلة غير أولية. نجاح build لا يقيس زمن التنزيل على جهاز فعلي.
- تدقيق الاعتماديات الإنتاجية في CI #41767787126 وجد **0 vulnerabilities** عند المستوى الذي يفحصه الأمر الحالي (`--omit=dev --audit-level=high`).
- في أحدث تشغيلين متاحين (`main` CI #41903896915 وPR #69 CI #41904767404، بتاريخ 2026-11-04)، وجد `npm audit --omit=dev --audit-level=high` **0 vulnerabilities** في اعتماديات الإنتاج. سجّل التدقيق الكامل **6 تنبيهات في شجرة التطوير: 2 Low و4 Moderate، وصفر High/Critical**. كان تشغيل PR #67 السابق #41876997024 قد سجّل **10 تنبيهات: 2 Low و8 Moderate**؛ لذلك نسجل النتائج بحسب رقم التشغيل ولا نفترض أن العدد ثابت. لا تُحدّث السلسلة عشوائيًا؛ افحص الشجرة والتوافق وPWA قبل أي ترقية.
- نتيجة تدقيق PR #67 CI [#41876997024](https://github.com/HVA09/lumen-learning-platform/actions/runs/41876997024): الإنتاج **0 vulnerabilities**؛ الشجرة الكاملة **10 تنبيهات (2 Low و8 Moderate؛ صفر High/Critical)**. في التشغيلين الأحدث [main #41903896915](https://github.com/HVA09/lumen-learning-platform/actions/runs/41903896915) و[PR #69 #41904767404](https://github.com/HVA09/lumen-learning-platform/actions/runs/41904767404)، انخفض التقرير المرصود إلى **6 تنبيهات (2 Low و4 Moderate)** مع بقاء الإنتاج عند صفر. سبب اختلاف لقطة قاعدة بيانات advisories بين التشغيلات غير محسوم؛ يجب الاحتفاظ بمراجع التشغيل وعدم تقديم العدد كخاصية ثابتة للـ lockfile.
- الإصدارات التي ظهرت في `frontend/package-lock.json`: `vite-plugin-pwa` 2.0.0 و`workbox-build` 7.4.1؛ `glob` 11.1.0 المتأثر بـ [GHSA-3g3m-2fjr-6pw4](https://github.com/advisories/GHSA-3g3m-2fjr-6pw4) والمصحح في 14.0.2؛ `minimatch` 10.2.6 ونسخة متداخلة 5.1.9 المتأثرتان بـ [GHSA-g3hv-75wg-m249](https://github.com/advisories/GHSA-g3hv-75wg-m249) والمصحح في 11.0.1. كما يتضمن المسار `ejs -> jake -> filelist -> minimatch` و`@trickfilm400/rollup-plugin-off-main-thread` 3.0.0-pre1.
- هذه تبعيات build/test عليها `dev: true` في lockfile، وليست حزم التشغيل. بعض تنبيهات EJS/Jake/Filelist مترابطة عبر minimatch؛ لا تُعامل EJS 3.1.10 على أنها مصابة بالثغرة القديمة التي عولجت في هذا الإصدار نفسه. لا تُنفّذ `npm audit fix --force` أو تخفيض `vite-plugin-pwa` إلى 1.1.0 دون اختبار؛ راجع ADR-033.
- المعالجة مؤجلة عمداً إلى تحديث متوافق من Workbox أو overrides محددة ومختبرة. لا تعدّل lockfile يدوياً؛ يجب توليده بواسطة npm وإثبات `npm ci` والاختبارات والبناء وسلوك Service Worker وفحص audit بعد التحديث.
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
- [CI #41767787126 — main بعد PR #57](https://github.com/HVA09/lumen-learning-platform/actions/runs/41767787126)

مهم: تغييرات P5.1–P5.3 أصبحت جزءًا من `main` بعد دمج PR #41 ثم #43 ثم #44 بالترتيب. نجاح CI لا يثبت تشغيلًا إنتاجيًا أو اختبار متصفح حي.

## 3. الأدوات والقدرات الموجودة في الواجهة

ملف `frontend/package.json` يحتوي scripts التالية فقط:

- `dev`
- `build`
- `preview`
- `test` — يشغّل `vitest run`

الاختبارات تستخدم Vitest وReact Testing Library وjsdom وفق إعداد `frontend/vite.config.js`.

لا يظهر حاليًا script مستقل لـ ESLint أو TypeScript typecheck أو browser end-to-end test في `package.json` أو CI. لا توجد حاليًا خطوة Playwright/Cypress في workflow المعتمد. كما لا تظهر حزم ESLint أو إضافاته في `frontend/package.json` الحالي؛ لذلك لم يتم قياس baseline للواجهة بعد.

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
| Lint للواجهة | غير مفعّل في main | لا توجد حزم أو config أو script ESLint معتمد. تجربة PR #55 ليست baseline رسميًا؛ أُزيلت findings المؤكدة في PR #56، ويتبقى تثبيت ESLint وReact Hooks plugin عبر npm ثم قياس كامل report-only |
| Type checking | لا يوجد TypeScript أو typecheck job | لا يوجد فحص أنواع آلي للواجهة |
| Lint للخلفية | Ruff 0.17.3 report-only | 0 diagnostics بعد PR #52 و#53؛ لا توجد بوابة منع، ولا حاجة لإعادة تصنيف F401 في baseline الحالي |
| تغطية الاختبارات | مجموعات اختبارات ناجحة | لا يوجد coverage baseline أو تقرير اتجاهات |
| Browser E2E | Playwright/Chromium عبر PR #70/#73/#75/#77/#80/#81/#82 | يغطي HttpOnly cookies والجلسة، الدرس والتقدم بعد reload، نشر الدرس، Quiz فارغ وحفظ history، تصحيح الإجابات الصحيحة عند عتبة البوابة، وقيود الواجهة/API للأدوار مع عزل ملكية الفصل. PR #82 يثبت دورة سؤال المعلم من الإنشاء والتعديل والتعطيل إلى الحذف. لا يثبت بعد جميع حالات التصحيح أو فحص ClamAV الحقيقي أو الإشعارات/WebSocket وRTL/LTR والانقطاع/العودة. |
| الأداء | PR #59/#62/#64/#65 فصلت الميزات الثقيلة؛ PR #67 خفّض Workbox precache من 35/1328.16 KiB إلى 8/378.63 KiB | لا توجد ميزانية أداء رقمية أو RUM/قياسات Core Web Vitals ميدانية؛ CacheFirst لا يجعل API/WebSocket تعمل دون اتصال |
| أمن اعتماديات التطوير | الإنتاج: 0 vulnerabilities؛ أحدث تدقيق كامل: 2 Low و4 Moderate؛ تشغيل سابق سجّل 2 Low و8 Moderate | التنبيهات تخص أدوات بناء PWA/Workbox والاعتماديات الانتقالية؛ اختلاف العدد بين التشغيلات موثق في ADR-033؛ المعالجة تتطلب تحديثًا متوافقًا وإعادة توليد lockfile واختبارات كاملة |
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
- النتيجة بعد PR #53، وتأكدت مرة أخرى على `main` بعد PR #54: **0 diagnostic(s)** في Ruff report-only.
- تحقق PR #53: CI #41757169187 نجح بالكامل؛ Backend **423 passed, 20 warnings**، وFrontend **73 passed عبر 14 ملفًا**، وproduction build وتدقيق الإنتاج وGitleaks وCompose وmigrations وPostgreSQL backup/restore وRestic smoke ناجحة.
- لا يستخدم CI `--fix` ولا يحوّل Ruff إلى شرط دمج؛ نجاح Ruff التشغيلي لا يلغي ضرورة إبقاء اختبارات Backend وFrontend والبناء وGitleaks إلزامية.

**الخطوة التالية — ESLint للواجهة، لم يبدأ التنفيذ بعد:**
1. مراجعة ملفات JSX/JS و`vite.config.js` واختيار إعداد ESLint متوافق مع React 19 وبيئة Vite وVitest.
2. إضافة الإصدارات المحددة إلى `frontend/package.json` وتوليد `frontend/package-lock.json` بواسطة npm نفسه؛ لا تعدّل lockfile يدويًا ولا تعتمد `npx` بإصدار عائم.
3. إثبات قابلية إعادة التثبيت عبر `npm ci`، ثم تشغيل lint على المصدر والاختبارات وجمع النتائج كـ report-only.
4. تصنيف findings وإصلاح دفعات صغيرة مع بقاء الاختبارات والبناء وGitleaks شروطًا إلزامية؛ لا تجعل ESLint required check قبل baseline مستقر.
5. لا يوجد ESLint executable/config/script معتمد في main. التجربة الجزئية في PR #55 أعطت إشارات فقط؛ أُصلحت ثلاثة findings مؤكدة في PR #56، ولا يجوز إعلان baseline رسمي قبل تثبيت ESLint وReact Hooks plugin وإعادة القياس.

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

**تقدم جزئي — PR #59 و#62 و#64 مدمجة:**
- PR #59 نقل `TopicPanel` إلى `React.lazy`، فهبط entry الأولي من **830.50 kB / 258.06 kB gzip** إلى نحو **362.86 kB / 116.80 kB gzip**.
- PR #62 أجّل Markdown/KaTeX renderer وCSS الخاص بهما إلى لحظة عرض MathText؛ حجم renderer **442.53 kB / 133.49 kB gzip** وCSS **30.20 kB / 8.08 kB gzip**، بينما wrapper لا يتجاوز **0.70 kB / 0.42 kB gzip**.
- PR #64 أجّل `QuizPanel` و`LabPanel` وكل محاكاة إلى أن يطلبها المتعلم. في main CI #41858290575: entry **362.89 kB / 116.82 kB gzip**، و`TopicPanel` **6.76 kB / 2.47 kB gzip** بدل 23.28/6.91، و`QuizPanel` **4.88/1.96**، و`LabPanel` **1.80/0.86**. ملفات المحاكاة الفردية تتراوح بين 1.82 و3.23 kB قبل الضغط.
- بقي `AdminDashboard` **401.91 kB / 110.80 kB gzip** و`MathTextRenderer` **442.53 kB / 133.49 kB gzip** كـ chunks مستقلة غير موجودة في entry الأولي.
- CI بعد PR #64: Backend **423 passed, 20 warnings**، Ruff **0 diagnostics**، Frontend **74 passed عبر 14 ملفًا**، build وGitleaks وmigrations وPostgreSQL backup/restore نجحت.
- هذه أرقام build فقط؛ لا تثبت زمن تنزيل فعلي أو Core Web Vitals أو تجربة شبكة بطيئة. أول استخدام للاختبار أو المختبر أو الرياضيات يحتاج تنزيل الجزء المقابل.

- PR #65 سجّل الاستماع إلى `vite:preloadError`، ويعيد تحميل الصفحة مرة واحدة كحد أقصى خلال 60 ثانية عندما يكون المتصفح متصلاً و`sessionStorage` متاحاً؛ إذا كان المتصفح offline أو التخزين محجوباً لا يُخفى الخطأ، بل يصل إلى ErrorBoundary. يعرض ErrorBoundary رسالة عربية خاصة بتحميل chunk، ويعطّل زر إعادة المحاولة حتى حدث `online`. اختبارات PR #65: **80 Frontend passed عبر 16 ملفاً**؛ Backend **423 passed, 20 warnings**؛ Ruff **0 diagnostics**. CI بعد الدمج #41861598602 نجح بالكامل: Backend **423 passed, 20 warnings**، Ruff **0 diagnostics**، Frontend **80 passed عبر 16 ملفًا**، build وGitleaks وmigrations وPostgreSQL backup/restore ناجحة.

- PR #67 (Workbox app-shell precache + runtime cache للقطع المؤجلة): [PR CI #41876997024](https://github.com/HVA09/lumen-learning-platform/actions/runs/41876997024) نجح بالكامل. تغيّر Workbox من **35 entries / 1328.16 KiB** إلى **8 entries / 378.63 KiB** (انخفاض تقريبي **71.5%**). القطع المؤجلة تُخزّن بعد أول طلب ضمن CacheFirst؛ API وWebSocket لم تُضف إلى هذا التخزين.
- أحدث تحقق على `main`: [CI #41903896915](https://github.com/HVA09/lumen-learning-platform/actions/runs/41903896915) نجح بالكامل: Backend **423 passed, 20 warnings**، Ruff **0 diagnostics**، Frontend **80 passed عبر 16 ملفًا**، production build، Gitleaks، migrations، Compose، Restic وPostgreSQL backup/restore ناجحة. أحدث تدقيق اعتمادات التطوير في هذا التشغيل: **6 (2 Low و4 Moderate)**؛ تدقيق الإنتاج: **0 vulnerabilities**.

- معالجة تنبيهات اعتماديات PWA/Workbox المحددة في ADR-033 دون تخفيض عشوائي أو تعديل lockfile يدوي.

**الخطوات التالية:**
- قياس زمن فتح الموضوع وأول درس وأول معادلة وفتح الاختبار/المختبر على هاتف واتصال بطيء؛ افصل زمن تحميل كل chunk عن زمن API.
- اختبار Vite preload recovery وErrorBoundary على متصفحات وهواتف فعلية مع انقطاع/عودة الشبكة، والتحقق من التحديثات القديمة للـ chunks؛ لا يُعد نجاح اختبارات الوحدة اختباراً ميدانياً.
- توسيع Playwright E2E تدريجيًا بعد أول smoke ناجح في PR #70: إكمال درس واختبار quiz، ثم مسارات teacher/admin، الملفات والإشعارات، RTL/LTR، وقطع الاتصال/عودته. لا تعتبر تغطية المصادقة وحدها تغطية شاملة للمنصة.
- قياس فتح الموضوع وأول درس وأول معادلة على هاتف واتصال بطيء، ثم اعتماد ميزانيات أداء رقمية من القياس لا من أحجام build وحدها.
- حافظ على شرط الميزانية صفر، ولا تضف خدمة مدفوعة أو تتطلب بطاقة.
## 7. بوابات لا يجوز تخفيفها

- Backend tests وFrontend tests/build وGitleaks تظل شروطًا أساسية.
- لا تستخدم `continue-on-error` لإخفاء فشل أمني أو فشل اختبار.
- لا تتجاوز فحص الأسرار، ولا تستثنِ مجلد اختبارات كاملًا.
- لا تضع أسرارًا أو بيانات مستخدمين في الاختبارات أو التقارير.
- لا تغيّر API أو قاعدة البيانات أو صلاحيات المستخدمين ضمن مشروع إعداد أدوات الجودة إلا بقرار منفصل.
- لا تفرض lint/typecheck جديدًا على كل الملفات قبل معرفة baseline وتصنيف النتائج.

## 8. نقطة الاستئناف

- PR #95 و#97 مدمجان، مع نجاح CI بعد الدمج #42113922307 و#42115046453 (4/4). PR #100 مدمج في `main` عند `2f77979fc735ea69690474bed60fce8a0c206fc7` لإضافة Backend coverage report-only؛ تشغيل CI بعد الدمج #42239814878 جارٍ عند إعداد هذا التحديث.
- PR #100 مدمج: يضيف تغطية Backend report-only واختبارات المهام الخلفية. على رأسه `bfc29eb7a02187b7830f30bda5e3a6b46960e6f4` نجحت الوظائف الأربع في CI #42124352248؛ Backend **431 passed, 20 warnings**، التغطية **89%**.
- P6.1: Ruff 0.17.3 report-only، 0 diagnostics؛ ESLint لم يُعتمد بعد.
- P6.5: PR #59/#62/#64/#65/#67 مدمجة؛ precache أصبح 8 entries/378.63 KiB بعد خفض يقارب 71.5%. لا يوجد قياس ميداني بعد.
- P6.6: Playwright + Chromium على production preview مع FastAPI وPostgreSQL وRedis وClamAV مؤقتة. PRs #70/#73/#75/#77/#80/#81/#82/#84/#87/#88/#89/#91/#95/#97 تغطي التسجيل والجلسة، التقدم والنشر، Quiz، الصلاحيات، إدارة الأسئلة، فحص الملفات، الإشعارات، RTL/LTR، واستعادة الجلسة بعد عودة الشبكة.
- تغطية Backend الحالية تقريرية وليست شرط دمج. تُراجع الوحدات منخفضة التغطية قبل اختيار أهداف إضافية؛ لا نرفع العتبة آليًا.
- حسابات الأدوار مؤقتة وترقيتها محصورة في PostgreSQL المحلي `lumen_e2e` مع guards على المضيف وDATABASE_URL؛ لا endpoint لترقية الأدوار في التطبيق.
- سلسلة LTI #16–#23 تحتاج إعادة تأسيس وخطة migration/integration مستقلة؛ لا تدمج مباشرة.
- لا يوجد نشر إنتاجي مثبت.
## 9. قياس تغطية Backend — PR #100 (2026-11-06)

- المصدر: PR [#100](https://github.com/HVA09/lumen-learning-platform/pull/100)، رأس الفرع `bfc29eb7a02187b7830f30bda5e3a6b46960e6f4`، وتشغيل CI [#42124352248](https://github.com/HVA09/lumen-learning-platform/actions/runs/42124352248). الوظائف الأربع نجحت: Backend tests، Frontend tests/build، Browser E2E، وFull Git history secret scan.
- أضيف `pytest-cov==7.1.0` إلى أدوات التطوير فقط. الأمر يستخدم `--cov=app --cov-branch` وينشئ `coverage.xml` ويعرض الأسطر غير المغطاة. لم يُفرض حد أدنى؛ التقرير تشخيصي حتى تُراجع المناطق الناقصة.
- النتيجة: **431 passed, 20 warnings in 183.07s**.
- تقرير Coverage.py: **4,375 statements، 410 missed، 942 branches، 142 partially covered، الإجمالي 89%**. استُبعدت 77 وحدة مكتملة التغطية من جدول التفاصيل.
- تحسنت `app/tasks.py` من **37% إلى 92%** بعد سبعة اختبارات تغطي Celery enqueue، والرجوع للإرسال المباشر عند غياب Celery أو فشل Redis، ومهمة الإرسال، والملخص الأسبوعي، وتذكير بطاقات المراجعة، وإغلاق جلسة قاعدة البيانات عند الخطأ. ما زالت أسطر استيراد Celery عند غياب المكتبة (87–91) غير مغطاة؛ لأن Celery مثبت في بيئة الاختبار.
- لا تفسّر 89% بوصفها ضمانًا لجودة كل المسارات أو اختبارًا بيئيًا. التقرير يخص `backend/app` ويجمع قياس الأسطر والفروع.

### مناطق ذات أولوية لاختبارات لاحقة

| الوحدة | التغطية الحالية | اتجاه الاختبار |
|---|---:|---|
| `app/services/lti_service.py` | 63% | تحقق OIDC/JWKS، حدود DNS، الرفض الآمن، واختبارات LMS sandbox لاحقًا |
| `app/services/email_service.py` | 62% | SMTP/TLS، أخطاء الاتصال، وعدم تسريب رموز التحقق وإعادة التعيين |
| `app/routers/files.py` | 81% | الرفع والتنظيف والحصص والعزل وفشل ClamAV |
| `app/services/malware_scanner.py` | 80% | ردود ClamAV غير الصالحة، انتهاء المهلة، وفشل الاتصال |
| `app/cache.py` | 75% | حالات Redis unavailable والرجوع الآمن |
| `app/tasks.py` | 92% | استيراد Celery غير المتاح بعده فقط |

- `app/create_admin.py` عند 0% هو مسار أداة تهيئة إدارية منفصل؛ لا نعتبر النسبة المنخفضة فيه سببًا لاستدعاء ترقية الأدوار من اختبارات عامة أو توسيع صلاحيات التطبيق.
- لا نعطي مزودي الدفع أولوية تطويرية؛ لا يوجد تفعيل أو نشر لخدمات دفع، وتفضيل المشروع الحالي هو تجاوز الدفع الإلكتروني.
- الخطوة التالية الموصى بها: اختبارات SMTP الآمنة وخدمة LTI وملفات/ClamAV، مع mocks وخدمات CI المؤقتة فقط؛ لا تفعيل لخدمات خارجية أو إعدادات إنتاج.

## 10. خط أساس تغطية Frontend — PR #102 (2026-11-06)

- المصدر: PR [#102](https://github.com/HVA09/lumen-learning-platform/pull/102)، رأس الفرع `58dbf951d478705240e3e5746dee0546967d9e52`، وتشغيل CI [#42207211737](https://github.com/HVA09/lumen-learning-platform/actions/runs/42207211737). اكتملت الوظائف الأربع بنجاح: Frontend tests/build، Backend tests، Browser E2E، وFull Git history secret scan.
- أضيف اعتماد تطوير `@vitest/coverage-v8@5.0.5` مطابق لإصدار Vitest `5.0.5`، مع أمر `npm run test:coverage`. نطاق التقرير: ملفات JS/JSX تحت `frontend/src`، مع استبعاد ملفات الاختبارات وتهيئة الاختبار. تبقى `npm test` كما هي.
- النتيجة: **91 اختبارًا ناجحًا عبر 17 ملف اختبار**. إجمالي التغطية: **31.80% statements (597/1,877)**، **35.72% branches (369/1,033)**، **28.82% functions (179/621)**، و**32.05% lines (559/1,744)**.
- النتيجة تقريرية فقط: لا يوجد `coverage.thresholds` ولا حد أدنى يمنع CI. مجلد `coverage/` ضمن `.gitignore`; لا نضيف التقارير المولدة إلى Git.

### توزيع التغطية وأولوية الاختبارات

| المجال/الوحدة | المؤشر المقاس | أولوية العمل التالية |
|---|---:|---|
| `App.jsx` | 0% | اختبارات تركيب التطبيق ومسارات التنقل والحالات الأساسية |
| `AdminDashboard.jsx` | 0% | اختبارات صلاحيات العرض وتدفقات الإدارة |
| `ContentManager.jsx` | 0% | اختبارات الإنشاء والتعديل والنشر والحذف وحدود الصلاحية |
| `FilesPanel.jsx` | 0% | اختبارات الرفع والتنزيل والأخطاء والحالات غير المصرح بها |
| واجهات API في `src/lib` | معظمها 0%؛ `api.js` نحو 17.39% statements | اختبارات adapters باستخدام mocks للطلبات والأخطاء، دون خدمات خارجية حقيقية |
| `LabPanel.jsx` والمحاكاة و`LearningPath.jsx` | 0% في الوحدات المعروضة | اختبار الحسابات والسلوك التعليمي قبل تفاصيل العرض |
| `QuizPanel.jsx` | 97.56% statements | تغطية الفروع المتبقية فقط |
| `TopicPanel.jsx` | 92.98% statements | تغطية الحالات والفروع غير المغطاة |
| Hooks الإشعارات | حتى 96% statements في المجموعة | استكمال الحالات الطرفية عند الحاجة |

- الوحدات ذات 0% ليست حكمًا بأنها معطوبة؛ معناها أن مجموعة الاختبارات الحالية لم تنفّذ أسطرها. لا تعالج ذلك باستثناء الملفات من التقرير أو باختبارات شكلية.
- لا تفسر 31.80% على أنها تقييم شامل لجودة المنصة أو اختبارًا ميدانيًا؛ إنها نقطة قياس أولية لنطاق JS/JSX المعلن، وليست دليلًا على أداء الهاتف أو RUM/Core Web Vitals.
- CI على PR #102 نجح 4/4؛ في تشغيله كانت اختبارات Backend **424 passed, 20 warnings**، ونجحت اختبارات المتصفح والبناء وتدقيق الاعتماديات الإنتاجية وفحص تاريخ Git.
- PR #102 لا يزال مفتوحًا وغير مدمج عند آخر تحقق. هذا القسم يوثق قياس رأس PR، ولا يدّعي أنه مدمج على `main`.
- فحص كامل التاريخ على رأس التوثيق `e0177a533e958ad9a972797e76eee447173dbfc2` التقط خمس قيم اختبارية قديمة في commit تاريخي من PR #103، لا بيانات اعتماد تشغيلية. القيم أزيلت من ملفات الاختبار الحالية واستبدلت بقيم مركبة غير سرية؛ أضيفت بصمات Gitleaks الخمس الدقيقة فقط إلى `.gitleaksignore`. لم نستثنِ ملفًا أو مسارًا أو قاعدة كشف أو تاريخًا، وتظل فحوص PR وجميع المراجع والتاريخ الكامل مفعّلة.



## 11. خط أساس الجودة الحالي على main — 2026-11-06 بعد PR #119

- رأس `main` الحالي بعد PR #123: `53a1912773dbbaf4a854ec7d110dc4fd46a2b6a3`.
- PR [#113](https://github.com/HVA09/lumen-learning-platform/pull/113): اختبارات حصص الملفات وClamAV fail-safe؛ CI [#42241558869](https://github.com/HVA09/lumen-learning-platform/actions/runs/42241558869) نجح 4/4؛ Backend 447 passed و21 warnings.
- PR [#117](https://github.com/HVA09/lumen-learning-platform/pull/117): اختبارات SMTP وLTI DNS/JWKS؛ CI [#42242688194](https://github.com/HVA09/lumen-learning-platform/actions/runs/42242688194) نجح 4/4؛ Backend 480 passed و21 warnings و90% coverage في 182.86 ثانية.
- PR [#119](https://github.com/HVA09/lumen-learning-platform/pull/119): تغطية Frontend واختبارات API adapters وFilesPanel وAdminDashboard وContentManager؛ CI [#42243595538](https://github.com/HVA09/lumen-learning-platform/actions/runs/42243595538) نجح 4/4.

### Backend — المقاييس الحالية

| الوحدة | Coverage |
|---|---:|
| `app/routers/files.py` | 82% |
| `app/services/email_service.py` | 92% |
| `app/services/lti_service.py` | 89% |
| `app/services/malware_scanner.py` | 93% |
| `app/tasks.py` | 92% |

- المجموع: 4,375 statements، 347 missed، 942 branches، 134 partially covered، الإجمالي 90%. هذه نتيجة pytest-cov report-only وليست ضمانًا للاكتمال.

### Frontend — المقاييس الحالية

- 142 اختبارًا ناجحًا عبر 24 ملف اختبار.
- Statements: 50.34% (945/1,877).
- Branches: 53.53% (553/1,033).
- Functions: 47.98% (298/621).
- Lines: 50.63% (883/1,744).

| الوحدة | Statements | الملاحظة |
|---|---:|---|
| `App.jsx` | 0% | أولوية الاختبارات التالية: مسارات المصادقة والجلسة والتنقل والأدوار والوحدات المؤجلة |
| `AdminDashboard.jsx` | 88.23% | تدفقات الإدارة والحماية الأساسية مغطاة؛ أكمل الحالات الطرفية |
| `ContentManager.jsx` | 75.25% | تغطية إنشاء/إدارة المحتوى تحسنت؛ راجع الفروع غير المغطاة |
| `FilesPanel.jsx` | 83.82% | تغطية عمليات الملفات الأساسية والأخطاء |
| `authApi.js`, `filesApi.js`, `quizApi.js`, `usersApi.js` | 100% لكل ملف | adapters مغطاة بالـ mocks |
| `LearningPath.jsx`, `LabPanel.jsx` والمحاكاة | 0% | أضف اختبارات قواعد التعليم والحسابات والسلوك |

- لا ترفع التغطية باستثناء ملفات أو اختبارات شكلية. لا يوجد `coverage.thresholds` مفروض؛ راجع الوحدات والمخاطر قبل إنشاء gate.
- CI بعد دمج PR #117 على `main` [#42243421397](https://github.com/HVA09/lumen-learning-platform/actions/runs/42243421397) وبعد PR #119 [#42244364141](https://github.com/HVA09/lumen-learning-platform/actions/runs/42244364141) نجحا 4/4. PR #123 تنظيف import فقط؛ CI [#42244746449](https://github.com/HVA09/lumen-learning-platform/actions/runs/42244746449) نجح 4/4. تشغيل `main` بعد PR #123 [#42245438258](https://github.com/HVA09/lumen-learning-platform/actions/runs/42245438258) ما زال قيد التنفيذ عند كتابة التحديث.
- ما زالت RUM/Core Web Vitals الميدانية وTypecheck/ESLint وقياسات هاتف واتصال بطيء غير مكتملة. لا يوجد نشر إنتاجي أو تكامل SMTP/LMS خارجي مثبت.


## 12. خط أساس Frontend بعد PR #141 — 2026-11-06

- PR #129/#133/#136/#137/#140/#141 مدمجة في `main`؛ CI الخاص بكل PR نجح 4/4. CI بعد PR #140 على main [#42254119108](https://github.com/HVA09/lumen-learning-platform/actions/runs/42254119108) نجح 4/4. CI بعد PR #141 على main [#42265976307](https://github.com/HVA09/lumen-learning-platform/actions/runs/42265976307) اكتمل بنجاح 4/4 في [CI #42265976307](https://github.com/HVA09/lumen-learning-platform/actions/runs/42265976307).
- CI PR #141 [#42265153710](https://github.com/HVA09/lumen-learning-platform/actions/runs/42265153710) نجح 4/4، وشغّل 187 اختبار Frontend عبر 28 ملفًا.

| المقياس | النتيجة | المغطى / الإجمالي |
|---|---:|---:|
| Statements | 70.83% | 1,341 / 1,893 |
| Branches | 65.26% | 682 / 1,045 |
| Functions | 60.16% | 376 / 625 |
| Lines | 71.85% | 1,261 / 1,755 |

### وحدات بارزة

| الملف | Statements | Branches | Functions | Lines |
|---|---:|---:|---:|---:|
| `App.jsx` | 75.00% | 75.00% | 49.05% | 80.18% |
| `LearningPath.jsx` | 100.00% | 93.54% | 100.00% | 100.00% |
| `LabPanel.jsx` | 100.00% | 100.00% | 100.00% | 100.00% |
| `CircuitSim.jsx` | 98.64% | 93.75% | 88.88% | 98.63% |
| `PythonLabSim.jsx` | 78.57% | 90.00% | 62.50% | 80.00% |

- Backend في CI نفسه: **480 passed، 21 warnings، 90% coverage**؛ migrations وPostgreSQL backup/restore integration smoke tests نجحت.
- يظل التغطية report-only ولا يوجد `coverage.threshold` مفروض. نتائج mocks تؤكد orchestration والسلوك المحلي ولا تثبت تشغيل Pyodide/CDN حي أو أداء هاتف حقيقي.
- لا يوجد RUM/Core Web Vitals instrumentation أو `web-vitals` dependency مثبتة. لا يوجد ESLint script/dependency أو TypeScript checker ضمن إعدادات Frontend الحالية؛ المصدر JavaScript/JSX.
- لا يوجد نشر إنتاجي مثبت. لا تعتبر CI بديلًا عن قياس جهاز حقيقي أو HTTPS/SMTP/ClamAV/backup على المضيف المستهدف.


## 9. خط أساس الجودة بعد PR #145/#147/#146 — 2026-11-07

### CI على رأس PR #146 بعد إعادة التأسيس

- الرأس: `4ea272d941d0a4042fdefb8f8a8c7267db2304b2`، بقاعدة `main` عند `d5245af119bc5737fd0e1822b886648013394e14`.
- CI [#42405345735](https://github.com/HVA09/lumen-learning-platform/actions/runs/42405345735) اكتمل بنجاح **4/4**: Backend، Frontend/build، Browser E2E، وFull Git history secret scan.
- Backend: **481 passed، 21 warnings** في 182.71 ثانية. التغطية **90%**: 4,375 statements، 347 missed، 942 branches، و134 partially covered. لا توجد عتبة coverage مفروضة؛ التقرير report-only.
- Frontend: **199 passed عبر 29 ملف اختبار**. V8 coverage report-only:
  - Statements: **72.46%** (1,458 / 2,012).
  - Branches: **65.82%** (728 / 1,106).
  - Functions: **64.56%** (410 / 635).
  - Lines: **73.15%** (1,368 / 1,870).
- `App.jsx`: 100% statements، 97.5% branches، 100% functions، 100% lines؛ `main.jsx` يبقى entry point غير مختبر مباشرة، ولا ينبغي تفسير 0% له كفشل في التطبيق. لا تُرفع النسبة باستثناء ملفات أو اختبارات شكلية.
- Browser E2E تحقق من تنفيذ Pyodide داخل Blob Worker فعلي ومنع الوصول إلى DOM والتخزين ومنع طلب API بواسطة CSP enforced، وتعافي WebSocket عبر حاوية Nginx، واستعادة جلسة المتصفح بعد عودة الاتصال، وتدفقات الدروس والاختبارات والملفات وفحص ClamAV.

### تفسير النتائج وحدودها

- مقارنة بآخر خط أساس موثق في PR #141 (187 frontend tests / 70.83% statements / 65.26% branches / 60.16% functions / 71.85% lines)، ارتفع القياس في هذا التشغيل إلى 199 tests و72.46% / 65.82% / 64.56% / 73.15%. هذه نتيجة CI الحالية، وليست performance metric أو ضمانًا لكل رحلة استخدام.
- CI على main بعد دمج #146 [#42405775181](https://github.com/HVA09/lumen-learning-platform/actions/runs/42405775181) كان قيد التنفيذ عند كتابة هذا التحديث؛ لا تسجل له نجاحًا قبل اكتماله.
- القياس report-only؛ لا يوجد coverage threshold. لا يزال RUM/Core Web Vitals على هاتف واتصال بطيء غير منفذ، ولا يوجد اختبار WSS/TLS حي أو LMS/SMTP خارجي.
