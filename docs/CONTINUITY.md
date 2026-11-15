# دليل استمرارية المشروع عبر الأجهزة والمحادثات

آخر تحديث: 2026-11-15

## أحدث نقطة استئناف — 2026-11-15 (LTI AGS delivery hardening)

- المستودع: `HVA09/lumen-learning-platform`. فرع العمل: `feat/lti-ags-rebased-20261115`.
- PR #154: https://github.com/HVA09/lumen-learning-platform/pull/154 — ما زال **Draft** عمدًا. لا تدمجه قبل اختبار Moodle Sandbox وCanvas Sandbox كلٌّ على حدة.
- آخر رأس تم التحقق من فحوصه قبل تحديث التوثيق: `daf23532d15893678dd9e949662885cd95779c4b`.
- آخر تشغيل CI على هذا الرأس: [43687381243](https://github.com/HVA09/lumen-learning-platform/actions/runs/43687381243) — **4/4 Success**. Backend: **497 passed, 21 warnings**؛ اختبار `test_ags_delivery_lease_blocks_second_independent_database_worker` نجح. Frontend production build، Browser E2E، وFull Git history secret scan نجحت.
- بعد هذه الجولة أضيف تحديث توثيقي إلى `backend/LTI_AGS_SANDBOX_RUNBOOK.md` لشرح lease ومددها ودورة حياة معاملات DB؛ سيحتاج الرأس الناتج إلى CI جديد قبل اعتماده على أنه متحقق.

### هندسة تسليم AGS الحالية في فرع PR #154

- نموذج `LTIAGSDeliveryLease` وجدول `lti_ags_delivery_leases` مع migration `0027_lti_ags_delivery_lease`.
- قفل فريد حسب `(assignment_link_id, SHA-256(lti_subject)))، مع `owner_token` ومدة lease مقدارها 120 ثانية؛ لا نخزن subject الخام في جدول القفل.
- معاملة قصيرة لحجز الحدث ثم `COMMIT` قبل OAuth/HTTP، ومعاملة منفصلة بعد الشبكة لتسجيل النتيجة والتحقق من مالك القفل وتحريره.
- مهلة DNS 10 ثوانٍ، والمهلة الخارجية الإجمالية لإرسال AGS 45 ثانية، أقصر من lease.
- مسارات الخروج المبكر تنفذ rollback لتحرير أقفال الصفوف، ومسار النجاح لا يقرأ ORM attributes بعد commit لتجنب فتح معاملة جديدة عن غير قصد.
- الاختبارات تغطي re-grade أثناء إرسال قديم بثلاث جلسات مستقلة: عامل أول، جلسة مصحح تنشئ الدرجة الجديدة، وعامل ثانٍ يحاول حجز القفل. يجب أن يفشل العامل الثاني أثناء lease ثم يرسل الدرجة الأحدث بعد تحرير القفل.
- الدلالة تبقى at-least-once لا exactly-once؛ أي نجاح CI محلي لا يحسم سلوك timestamp وإعادة الإرسال في Moodle/Canvas.

### البوابات المتبقية

1. إعادة تشغيل CI على آخر رأس بعد تحديث runbook والتأكد من نجاح 4/4.
2. Moodle Sandbox: تسجيل LTI 1.3، OIDC launch، Resource Link discovery، mapping، OAuth، grade passback وre-grade، timeout/retry، واختبارات السلوك المكرر.
3. Canvas Sandbox: السيناريو نفسه بشكل مستقل، مع التحقق من Line Item وGradebook وسلوك timestamps.
4. حفظ تقارير منقحة من دون ID tokens أو access tokens أو مفاتيح خاصة.
5. إبقاء PR #154 Draft وعدم الدمج حتى اكتمال بوابتي Moodle وCanvas.

لم تُجرَ تغييرات على قواعد بيانات منشورة أو أسرار LMS أو إعدادات الاستضافة أو بيانات طلاب حقيقية. هذا الفرع تطوير واختبار فقط.

---

## أحدث نقطة استئناف — 2026-11-07 (سجل تاريخي)


## أحدث نقطة استئناف — 2026-11-07

- `main`: `362aac61f3df486027eef014d3f6bc577cc2aa3d` بعد دمج PR #145 ثم #147 ثم #146. تفاصيل كل merge وCI في الملحق الأحدث نهاية الملف.
- CI PR #146: [#42405345735](https://github.com/HVA09/lumen-learning-platform/actions/runs/42405345735) نجح 4/4؛ Backend 481 passed/21 warnings/90% coverage، Frontend 199 passed/29 files و72.46% statements.
- CI بعد الدمج على main [#42405775181](https://github.com/HVA09/lumen-learning-platform/actions/runs/42405775181) كان قيد التنفيذ عند آخر تحقق؛ لا تعتمد نتيجته قبل مراجعته.
- Issue #134 ما زالت مفتوحة لمراجعة مختبر Python على المتصفح المستهدف وحدود الذاكرة؛ لا تعتبر Worker بيئة OS-level sandbox.

## نقطة الاستئناف — 2026-11-05

- رأس `main` الحالي بعد PR #123 هو `53a1912773dbbaf4a854ec7d110dc4fd46a2b6a3`. PR #100 و#109 و#113 و#117 و#119 و#123 مدمجة؛ Backend 480 passed و90%، وFrontend 142 passed عبر 24 ملفًا و50.34% statements. لا يوجد نشر إنتاجي مثبت.
- PR #87 أضاف إعادة اتصال WebSocket للإشعارات بانقطاع مؤقت بتأخير تصاعدي محدود (1–30 ثانية)، مع عدم إعادة المحاولة لرموز الإغلاق النهائية 1008 و4001، وتنظيف المؤقتات ومعالجات الأحداث عند إلغاء المكوّن. أضاف اختبارات Frontend واختبار Backend يثبت وصول الإشعار نفسه إلى جلستين مستقلتين للمستخدم نفسه وحفظه في سجل الإشعارات. PR CI #41959167152 وCI بعد الدمج على main [#42091787403](https://github.com/HVA09/lumen-learning-platform/actions/runs/42091787403) نجحا 4/4.
- PR #88 أضاف Browser E2E لمحاولة بوابة أقل من الحد (7/10 عند عتبة 80%)، والتحقق من تصحيح الخادم وحفظ نتيجة الرسوب في السجل ورفض إعادة المحاولة فورًا بـ HTTP 429. CI للـ PR [#42092155512](https://github.com/HVA09/lumen-learning-platform/actions/runs/42092155512) نجح 4/4؛ PR مدمج.
- CI بعد PR #88 على main [#42092874266](https://github.com/HVA09/lumen-learning-platform/actions/runs/42092874266) اكتمل بنجاح 4/4 على commit `92b05ca09c489857328647f42f61a39c969dea0f`.
- PR #89 أضاف اختبار Backend في `backend/tests/test_quiz.py`: نتيجة 7/10 (70%) لا تحقق عتبة 80%، ويؤكد الاختبار `passed=false` و`gateway_quiz_passed=false` وبقاء الموضوع التابع مقفلاً برمز HTTP 403. التغيير اختبار فقط ولا يغيّر منطق التطبيق. PR CI [#42101543986](https://github.com/HVA09/lumen-learning-platform/actions/runs/42101543986) نجح 4/4، ودُمج PR #89 عند `06a66e0e70dd2e929ab7a818ad65a96db11465a3`. CI بعد الدمج على main [#42102276661](https://github.com/HVA09/lumen-learning-platform/actions/runs/42102276661) اكتمل بنجاح 4/4.
- P6.6 يغطي التسجيل والجلسة، الدرس والتقدم والنشر، Quiz وسجل المحاولات واجتياز البوابة عند الحد والرسوب أسفله، الأدوار وعزل الفصول، إدارة الأسئلة، ClamAV الحقيقي، وإعادة اتصال الإشعارات وتعدد الجلسات، واختبار اتجاه المستند RTL/LTR عبر PR #91.
- اكتملت تغطية تبديل `dir` و`lang` بين العربية والإنجليزية والعودة عبر PR #91؛ لا يعني ذلك أن كل نصوص التطبيق مترجمة.
- PR #95 مدمج عند `80be944a39ffd683daa4ee24cabe48a3bd9067c7`؛ يعيد محاولة تهيئة الجلسة بعد عودة الاتصال، ويمنع إعادة التهيئة بعد login/logout، مع خمسة اختبارات مركزة. CI PR #42108841308 وما بعد الدمج #42113922307 نجحا 4/4.
- PR #97 مدمج: Browser E2E يعطّل أول GET /users/me بسبب انقطاع الشبكة، ثم يعيد المتصفح Online ويتحقق من استجابة 200 وعودة لوحة التعلم دون reload. لا يعني ذلك أن API أو التطبيق يعملان دون اتصال أو يعيدان إرسال طلبات الكتابة.
- PR #100 مدمج في `main` عبر `2f77979fc735ea69690474bed60fce8a0c206fc7`. القياس المدمج report-only: 431 Backend tests passed، 20 warnings، Coverage 89% على رأس PR السابق للدمج؛ لا يوجد حد أدنى مفروض.
- لا يوجد نشر إنتاجي مثبت؛ لا تنشئ موارد مدفوعة أو تتجاوز CI أو branch protection. المرجع التفصيلي للحالة والخطوات هو docs/PROJECT_STATUS.md، وللقرارات docs/DECISIONS.md، وللتحقق docs/QUALITY_BASELINE.md.

## الهدف

هذا الدليل يمنع اعتماد متابعة Lumen على محادثة واحدة أو هاتف واحد. سجل المشروع الرسمي موجود في GitHub، ويمكن فتحه من أي هاتف أو حاسوب متصل بالإنترنت.

## المرجع الذي نعود إليه دائمًا

افتح هذا المستودع:
https://github.com/HVA09/lumen-learning-platform

ثم افتح الملفات بهذا الترتيب:

1. `docs/PROJECT_STATUS.md` — ما الحالة الحالية؟ وما الذي اكتمل وما الذي بقي؟
2. `docs/DECISIONS.md` — ما القرارات التي اتُّخذت ولماذا؟
3. `docs/PROJECT_CHARTER.md` — ما الهدف والقيود الثابتة؟
4. سجل commits وPR وGitHub Actions — ما الذي تغيّر فعليًا وما الاختبارات التي نجحت؟

الصفحات المباشرة:
- [الحالة](https://github.com/HVA09/lumen-learning-platform/blob/main/docs/PROJECT_STATUS.md)
- [القرارات](https://github.com/HVA09/lumen-learning-platform/blob/main/docs/DECISIONS.md)
- [ميثاق المشروع](https://github.com/HVA09/lumen-learning-platform/blob/main/docs/PROJECT_CHARTER.md)
- [استمرارية العمل](https://github.com/HVA09/lumen-learning-platform/blob/main/docs/CONTINUITY.md)


## عند فتح ChatGPT من جهاز آخر

1. تأكد أنك داخل **حساب ChatGPT نفسه** الذي استخدمته على الجهاز الأول.
2. افتح قائمة المحادثات وابحث عن هذه المحادثة. إن لم تظهر، لا تبدأ من افتراض أن المشروع ضاع؛ افتح مستودع GitHub واقرأ ملفات الحالة والقرارات أعلاه.
3. ابدأ محادثة جديدة عند الضرورة، وأرسل النص التالي:

```text
تابع تطوير مشروع Lumen Learning Platform من المستودع:
https://github.com/HVA09/lumen-learning-platform

قبل أي تعديل:
1) اقرأ docs/PROJECT_STATUS.md وdocs/DECISIONS.md وdocs/PROJECT_CHARTER.md وdocs/CONTINUITY.md من أحدث فرع/commit.
2) تحقق مباشرة من حالة main وPRs وGitHub Actions، ولا تعتمد على ملخص محادثة قديم.
3) حافظ على ميزانية صفر، ولا تتطلب بطاقة أو دفعًا إلكترونيًا.
4) لا تعدّل main مباشرة ولا تتجاوز اختبارات CI أو فحوصات الأمن.
5) بعد كل مرحلة، حدّث ملفات التوثيق مع SHA وروابط الاختبارات والمهام المتبقية.
6) أخبرني بما تم فعليًا وما لم يتم، ولا تدّعِ الدمج أو النشر دون التحقق.
```

## كيف نحافظ على التوثيق من الآن

بعد كل مرحلة مهمة:
- حدّث `PROJECT_STATUS.md` بالـ commit الجديد، نتيجة CI، وما اكتمل وما بقي.
- أضف قرارًا جديدًا في `DECISIONS.md` إذا تغيرت بنية أو سياسة أو أداة أو طريقة نشر.
- حدّث `PROJECT_CHARTER.md` فقط عندما تتغير القيود أو الأهداف الأساسية.
- سجّل المشكلات المفتوحة بدل حذفها أو اعتبارها منتهية.
- لا تضع أسرارًا أو رموز وصول أو كلمات مرور في أي ملف توثيق.

## ملاحظة مهمة عن سجل محادثات ChatGPT

توثيق GitHub يحفظ **المشروع وقراراته التقنية**، لكنه لا يستطيع إصلاح مزامنة سجل محادثات ChatGPT نفسه أو إجبار التطبيق على إظهار محادثة مفقودة. لحفظ المحادثات:
- استخدم الحساب نفسه على الجهازين وتأكد من طريقة تسجيل الدخول نفسها.
- تجنب المحادثة المؤقتة عند الحاجة إلى الاحتفاظ بالسجل.
- تحقق من الأرشيف ومن إعدادات سجل المحادثات/البيانات إذا اختفت محادثة.
- إذا بقيت المحادثة مفقودة، راجع مركز مساعدة OpenAI أو حالة الخدمة؛ لا تحذف التطبيق أو بياناته قبل التأكد من تزامن محادثاتك المهمة.

حتى لو تعذر استرجاع محادثة، يبقى سجل التطوير في GitHub هو المرجع الذي يسمح باستمرار العمل.


## ملحق استمرارية — آخر تحقق 2026-11-06

- `main` بعد دمج PR #100: `2f77979fc735ea69690474bed60fce8a0c206fc7`.
- PR #95 وPR #97 مدمجان؛ استعادة جلسة المستخدم بعد عودة الشبكة واختبار المتصفح Offline → Online دون reload مكتملان، وتشغيل main CI #42115046453 نجح 4/4.
- PR #100 مدمج في `main`: [test(backend): report coverage and verify background tasks](https://github.com/HVA09/lumen-learning-platform/pull/100)، Squash commit `2f77979fc735ea69690474bed60fce8a0c206fc7`.
- أحدث تشغيل PR CI [#42124352248](https://github.com/HVA09/lumen-learning-platform/actions/runs/42124352248) نجح 4/4. Backend **431 passed, 20 warnings**، وCoverage **89%**. اختبارات `test_tasks.py` السبعة نجحت، ورفعت `app/tasks.py` إلى 92%.
- قياس التغطية report-only؛ لا حد أدنى ولا تعديل لإعدادات الإنتاج. لا تعتبر نتيجة PR مدمجة قبل التحقق من merge commit وحالة `main).
- الخطوة الحالية: التحقق من CI بعد دمج #100، وإصلاح/إكمال اختبارات SMTP وLTI/OIDC/SSRF وملفات/ClamAV على فروع مستقلة. PR #105 لديه إصلاح لاختبار حصة الملفات وCI جارٍ؛ لا تدمجه قبل نجاح الوظائف الأربع.
- لا يوجد نشر إنتاجي مثبت؛ نجاح CI لا يثبت SMTP فعليًا أو LMS sandbox أو موارد ClamAV على مضيف حقيقي.

## نقطة استئناف محدثة — 2026-11-06

1. `main` بعد PR #100 عند `2f77979fc735ea69690474bed60fce8a0c206fc7`؛ PR #95 و#97 و#100 مدمجة، ولا يوجد نشر إنتاجي مثبت.
2. PR #100: Backend report-only coverage؛ رأس الفرع وقت كتابة التحديث `5c840464e66543a21e3398491da6ca7095896442`. قياس رأس الاختبارات `bfc29eb7a02187b7830f30bda5e3a6b46960e6f4`: **431 passed, 20 warnings, 89%**؛ CI على رأس الاختبارات #42124352248 ورأس الوثائق #42125492215 نجح 4/4.
3. PR #102: Frontend V8 coverage report-only؛ رأس `58dbf951d478705240e3e5746dee0546967d9e52`؛ **91 passed عبر 17 ملفًا**، التغطية **31.80% statements / 35.72% branches / 28.82% functions / 32.05% lines**؛ CI #42207211737 نجح 4/4.
4. PR #100 مدمج، بينما PR #102 ما زال مفتوحًا. لا تدّعِ أن قياس Frontend صار baseline مدمجًا قبل تحقق دمجه على `main`.
5. الخطوة التالية: اختبارات Frontend مركزة لوحدات API ثم App/Admin/ContentManager/Files، ثم Backend SMTP وLTI/OIDC وFiles/ClamAV. حافظ على عدم تغيير API/DB/migrations في مرحلة الاختبار، وعلى شرط الميزانية صفر.



## نقطة استئناف مؤكدة — 2026-11-06 بعد دمج PR #119

- `main`: `53a1912773dbbaf4a854ec7d110dc4fd46a2b6a3`.
- PR #113 دمج اختبارات ملفات/ClamAV: CI #42241558869 نجح 4/4، 447 Backend passed.
- PR #117 دمج اختبارات SMTP وLTI DNS/JWKS: CI #42242688194 نجح 4/4، 480 Backend passed، 21 warnings، 90% coverage.
- PR #119 دمج خط أساس Frontend V8 report-only واختبارات API/files/admin/content: CI #42243595538 نجح 4/4؛ 142 اختبارًا عبر 24 ملفًا، statements 50.34%، branches 53.53%، functions 47.98%، lines 50.63%.
- CI بعد PR #117 على `main` [#42243421397](https://github.com/HVA09/lumen-learning-platform/actions/runs/42243421397) وبعد PR #119 [#42244364141](https://github.com/HVA09/lumen-learning-platform/actions/runs/42244364141) نجحا 4/4. PR #123 أزال import غير مستخدم؛ CI [#42244746449](https://github.com/HVA09/lumen-learning-platform/actions/runs/42244746449) نجح 4/4، وتشغيل `main` بعده [#42245438258](https://github.com/HVA09/lumen-learning-platform/actions/runs/42245438258) قيد التنفيذ عند آخر تحقق.
- لا تغييرات runtime/API/DB/migrations في PRs #113/#117/#119. لا يوجد threshold للتغطية. SMTP وLTI tests تستخدم test doubles؛ لا تثبت تكامل مزود بريد أو LMS خارجي فعلي.
- التالي: `App.jsx` integration tests، ثم `LearningPath` و`LabPanel` والمحاكاة؛ بعد ذلك RUM/Core Web Vitals وTypecheck وقياسات الهاتف. P7 والنشر الإنتاجي ما زالا غير مكتملين.
- حافظ على قيود الميزانية صفر، وعدم طلب بطاقة أو تفعيل دفع، وعدم تجاوز CI أو branch protection.


## نقطة استئناف مؤكدة — 2026-11-06 بعد PR #141

- `main`: `1f76de769a224fb01c5ac66e9bccede331650dac`.
- PR #129: اختبار StrictMode لـ session bootstrap؛ PR CI #42247388390 نجح 4/4.
- PR #133: reconnect فوري لـ notifications عند حدث `online` مع إلغاء backoff timer؛ PR CI #42248648649 نجح 4/4.
- PR #136: فصل تحميل LearningPath عن بيانات streak الاختيارية، واختبارات التحميل وحالات الموضوع وإلغاء تحديث الحالة بعد unmount؛ CI #42250578866 نجح 4/4.
- PR #137: اختبارات lazy simulation routing وfallback في LabPanel؛ CI #42251617174 نجح 4/4.
- PR #138: تحديث خريطة بنية Frontend؛ CI #42252349059 نجح 4/4.
- PR #140: حسابات math/physics/circuits وتحدي Python؛ CI #42253279488 نجح 4/4، وmain CI #42254119108 نجح 4/4.
- PR #141: animation/failure paths؛ CI #42265153710 نجح 4/4، وتم الدمج عند `1f76de769a224fb01c5ac66e9bccede331650dac`. main CI بعد الدمج #42265976307 اكتمل بنجاح 4/4 في [CI #42265976307](https://github.com/HVA09/lumen-learning-platform/actions/runs/42265976307).
- Frontend في PR CI #42265153710: 187 passed / 28 files؛ 70.83% statements، 65.26% branches، 60.16% functions، 71.85% lines.
- Backend في PR CI #42265153710: 480 passed، 21 warnings، 90% coverage؛ migrations وPostgreSQL backup/restore integration checks نجحت.
- لا يعني نجاح هذه الفحوص اختبارًا على هاتف حقيقي أو قياس RUM/Core Web Vitals أو نشرًا إنتاجيًا.

### الاستئناف التالي

1. تحقق من اكتمال main CI #42265976307 بعد PR #141.
2. حدّث QUALITY_BASELINE وPROJECT_STATUS وARCHITECTURE_PLAN وDECISIONS بالأرقام والقرارات الجديدة.
3. أكمل P6 بقياس ميداني للأداء وتجربة هاتف واتصال بطيء، وتقييم ESLint أو فحص JS ساكن دون فرض gate عشوائي.
4. أعد تقييم سلسلة LTI/AGS #16–#23 من commit graph حديث؛ هذه الفروع ما زالت متراكبة على bases قديمة ولا تدمج مباشرة.
5. أبقِ P7 مفتوحة حتى إثبات الاستضافة وHTTPS وSMTP وClamAV والنسخ الاحتياطي والاستعادة على مضيف إنتاجي مجاني مناسب.

- لا موارد مدفوعة أو طلب بطاقة. لا تتجاوز حماية الفرع أو فحوص CI والأمن.


## نقطة استئناف مؤكدة — 2026-11-07 بعد PRs #145/#147/#146

- المستودع الصحيح: `HVA09/lumen-learning-platform`. رأس `main` عند آخر تحقق: `362aac61f3df486027eef014d3f6bc577cc2aa3d` بعد دمج #146.
- PR #145 مدمج عند `11969f183d18d33028bc37ec53e7ecbf4ee4e11f`. CI PR #42295018064 وmain #42404350575 نجحا 4/4.
- PR #147 مدمج عند `d5245af119bc5737fd0e1822b886648013394e14`. CI على رأس الفرع النهائي #42404937903 وmain بعد الدمج #42405264997 نجحا 4/4.
- PR #146 مدمج عند `362aac61f3df486027eef014d3f6bc577cc2aa3d`. CI على رأس الفرع المحدث #42405345735 نجح 4/4: Backend 481 passed / 21 warnings / 90% coverage؛ Frontend 199 passed عبر 29 ملفًا؛ Browser E2E وفحص التاريخ الكامل للأسرار نجحا.
- CI على main بعد #146 هو [#42405775181](https://github.com/HVA09/lumen-learning-platform/actions/runs/42405775181) وكان قيد التنفيذ عند آخر تحقق. ابدأ أي عمل جديد بعد التحقق من نتيجته ورأس main الحالي.
- تفاصيل مختبر Python وقيوده في `docs/PYTHON_LAB_SECURITY.md`. هذا عزل متصفح/أصل وليس OS sandbox، ولا توجد ذاكرة Worker بحد صلب. لا تعلن تشغيل الكود العدائي بأمان.
- لا يوجد نشر إنتاجي مثبت. إعداد TLS معطل حتى وجود دومين وشهادة؛ يلزم اختبار WSS حي بعد تفعيل TLS. لا تعتبر اختبار Nginx المحلي بديلًا عن ذلك.
- المتبقي قبل إغلاق P6/P7: قياس ميداني RUM/Core Web Vitals، اختبار هاتف واتصال بطيء، تقييم ESLint/typecheck تدريجي، تحقق TLS/WSS على مضيف فعلي، اختبار Moodle/Canvas Sandbox، SMTP حي، قياس موارد ClamAV، وتهيئة Restic إلى وجهة خارجية مع استعادة فعلية.
- سلسلة LTI/AGS القديمة #16–#23 تبقى مستقلة ومتراكبة على قواعد قديمة؛ لا تُدمج مباشرة. أعد تأسيسها على main الحالي فقط بعد مراجعة migration graph وOIDC/AGS والاختبار.
- لا موارد مدفوعة ولا بطاقة ولا دفع إلكتروني. لا تعدّل main مباشرة ولا تتجاوز CI/branch protection.

### نص الاستئناف من جهاز آخر

تابع من `docs/PROJECT_STATUS.md` و`docs/DECISIONS.md` و`docs/PR_STACK_TRIAGE.md` بعد فحص main وCI مباشرة. آخر عمل مدمج في هذه المرحلة هو #145 ثم #147 ثم #146؛ لا تخلط هذا المستودع مع أي مشروع آخر.


---

## نقطة تحقق مؤكدة — 2026-11-15: LTI 1.3 / AGS 2.0

- المستودع: `HVA09/lumen-learning-platform`.
- `main` (آخر تحقق): `5a065c00ff739c21cad06d551c7e3aa51a3d604b`.
- طلب العمل: [PR #154](https://github.com/HVA09/lumen-learning-platform/pull/154)، ما زال **Draft**، ولم يُدمج. رأسه عند آخر نقطة تحقق قبل هذا التحديث: `f98990e6c48ad4c291169293caff114e14a89732`.
- آخر تشغيل CI للرأس المذكور: [#43744257767](https://github.com/HVA09/lumen-learning-platform/actions/runs/43744257767)، اكتمل **4/4 Success**: Backend tests، Frontend tests and production build، Browser E2E، Full Git history secret scan.
- ملخص Backend: **515 passed، 12 warnings، 89% coverage** على Python 3.12؛ تغطية report-only وليست حد قبول مفروضًا.
- التغيير يعيد تأسيس LTI 1.3 وAGS 2.0 على main الحالي: ربط Resource Link المحدد، outbox للدرجات، migrations 0023–0027، إدارة مفاتيح OAuth/JWT، وإدارة تسليم عبر lease لكل `(assignment_link_id, SHA-256(lti_subject))`.
- العامل يحجز ويُحدّث الحدث في معاملة قصيرة، ثم ينهي المعاملة قبل OAuth/HTTP؛ DNS محدود بـ10 ثوانٍ وAGS الخارجي بـ45 ثانية، ومدة lease 120 ثانية. بعد الشبكة يبدأ معاملة قصيرة ثانية ويتحقق من owner token. اختبارات التزامن تستخدم جلسات مستقلة للعامل الأول ومصحح الدرجة والعامل الثاني.
- لا تزال دلالة outbox **at-least-once** وليست exactly-once؛ احتمال إعادة إرسال score موجود عند قبول LMS للدرجة وفقدان الرد.
- بوابات ما قبل الدمج غير المكتملة: تسجيل الأداة وإعداد OIDC وAGS، اختبار launch، discovery وربط Resource Link، OAuth token endpoint، وصول الدرجة إلى Gradebook، re-grade، timeouts/retries، وحالات الفشل السلبية — كل ذلك في **Moodle Sandbox وCanvas Sandbox كلٌ على حدة**. لم نستخدم أسرار أو بيانات طلاب حقيقية، ولم نغيّر قاعدة بيانات منشورة أو إعدادات استضافة.
- القرار: لا ترفع الطلب من Draft ولا تدمجه حتى توثيق نتائج Sandbox الفعلية ومراجعة نتائج التسليم المتكرر وtimestamps. نجاح CI وحده لا يثبت توافق LMS الفعلي.
- الخطوة التالية: تنفيذ دليل `backend/LTI_AGS_SANDBOX_RUNBOOK.md` على Moodle وCanvas Sandbox منفصلين، ثم تسجيل إصدارات المنصتين ونتائج كل سيناريو في سجل الاختبار. إذا لم تتوفر حسابات Sandbox أو مفاتيح/أسرار تجريبية، يبقى هذا الحاجز مفتوحًا ولا تُخمن قيمه.


---

## مراجعة هندسية مؤكدة — PR #154 — 2026-11-15 (CI 43752535816)

- الرأس الذي اجتاز الفحوص: `968a100c196f2caf968aec3690e4a24c6d728684`; [CI #43752535816](https://github.com/HVA09/lumen-learning-platform/actions/runs/43752535816) **4/4 Success** بتاريخ 2026-11-15.
- Backend: **515 passed، 12 warnings، 89% coverage** (Python 3.12). Frontend tests/build، Browser E2E، وFull Git history secret scan نجحت. Ruff سجّل 6 diagnostics في وضع report-only؛ لم يُفرض gate جديد ولم تُخفّف أي قاعدة.
- فشلان سابقان في سلسلة إعادة تأسيس الاختبارات عولجا على رؤوس لاحقة: #43743363786 كشف أن fixtures لم تُنشئ Resource Link discovery قبل mapping، ثم #43743857525 كشف assertion قديمًا يتوقع `lineitem_ready=false` رغم وجود scope وlineitem صالحين. تم تحديث fixtures/assertion، والرأس الحالي اجتاز الاختبارات كلها.
- Migration `0027_lti_ags_delivery_lease` متسلسلة بعد 0026، وتضيف جدول lease بمفتاح فريد `(assignment_link_id, subject_hash)`، وFK إلى mapping مع CASCADE، وFK إلى event مع SET NULL، وفهرس `locked_until`. لا تضيف backfill أو تعديلًا لبيانات المستخدمين. CI تحقق من migrations ومن downgrade/backup/restore على قواعد اختبار مؤقتة فقط؛ لم تُشغّل أي migration إنتاجية.
- مراجعة dispatch: owner token عشوائي بطول 32 hex؛ upsert ذري لا يستولي على lease إلا إذا كان `locked_until` فارغًا أو منتهيًا؛ تُحفظ محاولة الحدث وlease في معاملة قصيرة ثم `COMMIT` قبل OAuth/HTTP. بعد الشبكة تُفتح معاملة قصيرة ثانية ويُشترط تطابق owner token قبل كتابة النتيجة أو تحرير القفل.
- حدود الشبكة: DNS resolver بحد 10 ثوانٍ، HTTP client بحد 15 ثانية لكل تبادل، وحد كلي 45 ثانية حول token + score delivery، مقابل lease مدته 120 ثانية. لا تتبع redirects، وتُستخدم DNS-pinned public addresses وTLS SNI. لا تبقى معاملة DB مفتوحة خلال I/O الخارجي وفق اختبار الجلسة.
- ترتيب الدرجات: قفل submission أثناء re-grade، grade_version متزايد، timestamps محفوظة ومتزايدة، وتُعلّم الأحداث الأقدم superseded قبل إرسالها إذا كانت النسخة الأحدث موجودة قبل الحجز. عند re-grade أثناء إرسال قائم، يمنع lease العامل الثاني حتى ينتهي الأول ثم يرسل الأحدث.
- الدلالة تبقى **at-least-once**: قبول LMS للدرجة ثم ضياع الرد أو توقف العامل قد يؤدي إلى إعادة إرسال الدرجة نفسها لاحقًا مع timestamp أحدث. لا يوجد إثبات exactly-once.
- فجوة اختبارات موثقة: توجد اختبارات جلسات DB مستقلة (عامل أول، re-grade، عامل ثانٍ) واختبار منع التوازي، لكن لا يوجد حتى هذا الرأس اختبار regression مباشر لانتهاء lease ثم استيلاء عامل جديد، ولا اختبار يثبت أن عاملًا قديمًا لا يستطيع finalize بعد انتقال owner token، ولا محاكاة كاملة لحالة قبول LMS ثم فقدان الاستجابة. أضف هذه الاختبارات قبل اعتبار سلوك expiry/recovery مثبتًا بالكامل؛ لا تفترضها من الاختبار الحالي.
- مراجعة OIDC/AGS: state hash أحادي الاستخدام مع cookie خاص بالمتصفح، nonce، issuer/audience/azp، deployment، target_link_uri، message type/version، وResource Link claims؛ مفاتيح JWKS تجلب عبر اتصال DNS-pinned عام دون redirects وبحد 1 MiB. OAuth client assertion RS256 قصيرة العمر وبـ score scope. الإدارة وعمليات retry محمية بـ `require_admin`، وAPI سجل الدرجات لا يعرض subject أو score أو raw lineitem أو OAuth material، وأخطاء التسليم المخزنة منقحة.
- نقطة توافق تحتاج إثباتًا خارجيًا: التحقق الحالي يشترط أن يكون lineitem على origin نفسه لـ OAuth token endpoint. هذا يقلل مساحة SSRF، لكنه قد يرفض إعدادات LMS التي تفصل API origin؛ لا تغيّره دون إثبات من Moodle وCanvas Sandbox.
- بوابة خارجية ما زالت مانعة: لا توجد في سياق التنفيذ حسابات/بيانات اعتماد Moodle Sandbox أو Canvas Sandbox متاحة للتحقق الفعلي. لم نحاول الاتصال بمنصات مجهولة ولم نستخدم أسرارًا أو بيانات طلاب. يلزم اختبار مستقل لكل منصة: registration، OIDC launch، discovery/mapping، OAuth، Gradebook passback، re-grade، retry/timeouts، duplicate/uncertain delivery، والفشل السلبي.
- حالة PR عند هذا التحقق: #154 مفتوح وDraft وغير مدمج؛ `main` ثابت عند `5a065c00ff739c21cad06d551c7e3aa51a3d604b`. نجاح CI لا يرفع Draft ولا يغلق بوابة Sandbox.


---

## تحديث تحقق PR #154 — 2026-11-15 — CI 43753017021

- الرأس: `fb158224d588ea6af0b8bb4d740abcd680aed991`; [CI #43753017021](https://github.com/HVA09/lumen-learning-platform/actions/runs/43753017021) اكتمل **4/4 Success**.
- Backend: **515 passed، 12 warnings، 89% coverage**؛ Frontend tests/build، Browser E2E، وFull Git history secret scan كلها Success. تشغيل CI أكد migrations وbackup/restore على PostgreSQL مؤقت، ولم ينفذ أي تغيير إنتاجي.
- Ruff ما زال report-only ويعرض 6 تشخيصات F401/F841 في `backend/tests/test_lti_ags_protocol.py` (imports غير مستخدمة ومتغير محلي غير مستخدم). ليست فحوصًا فاشلة ولا تم تغيير إعدادات lint؛ يمكن تنظيفها لاحقًا في تغيير مستقل صغير.
- تم فحص Issue [#155](https://github.com/HVA09/lumen-learning-platform/issues/155) ومعايير قبوله: إضافة تحقق مباشر من lease expiry/recovery، stale-owner fencing، قبول LMS مع فقدان الرد، وقياس عدم استنزاف DB pool تحت عدة أهداف متزامنة. الاختبارات الحالية تثبت الجلسات المستقلة ومنع التوازي والترتيب، لكنها لا تثبت كل هذه الحالات؛ أبقِ هذه الفجوات مفتوحة ولا تدّعِ اكتمالها.
- PR #154 لا يزال Open + Draft وغير مدمج؛ `main` لم يتغير عن `5a065c00ff739c21cad06d551c7e3aa51a3d604b`. لا توجد حسابات/بيانات اعتماد Sandbox متاحة في هذا التنفيذ، لذلك Moodle وCanvas E2E ما زالا مانع الدمج.

---

## تحديث تحقق PR #154 — 2026-11-15 — CI 43753460406

- الرأس الحالي الذي فُحص: `1c70f281ca34f6d0a58398491e376d50a798c008` على الفرع `feat/lti-ags-rebased-20261115`. المقارنة مع `main` عند `5a065c00ff739c21cad06d551c7e3aa51a3d604b` تُظهر 26 commit أمامًا و0 خلفًا؛ PR يحتوي 29 ملفًا متغيرًا. آخر commit على الرأس الحالي توثيقي فقط.
- [CI #43753460406](https://github.com/HVA09/lumen-learning-platform/actions/runs/43753460406) اكتمل **4/4 Success** على هذا الرأس: Backend tests، Frontend tests and production build، Browser E2E، وFull Git history secret scan.
- Backend على Python 3.12: **515 passed، 12 warnings، 89% coverage**. فحوص migration preservation/downgrade وPostgreSQL backup/restore على قواعد مؤقتة نجحت؛ لم تُنفذ migration على الإنتاج.
- Ruff ما زال **report-only**: 6 تشخيصات في `backend/tests/test_lti_ags_protocol.py` (5 × F401 و1 × F841). ليست فحوصًا فاشلة، ولم تُخفّف أي gate.
- المراجعة الحالية أكدت أن migration 0027 تضيف unique key على `(assignment_link_id, subject_hash)`، وFK إلى assignment link بـ CASCADE، وFK إلى grade event بـ SET NULL، وفهرس `locked_until`؛ downgrade يحذف الفهرس والجدول. لا يوجد backfill في هذه migration.
- dispatch يحجز lease عبر upsert مشروط بانتهاء القفل، ويستخدم owner token، ثم ينفذ COMMIT قبل OAuth/HTTP. بعد الشبكة يتحقق من owner token قبل finalization. مدة lease 120 ثانية، DNS timeout 10 ثوانٍ، HTTP timeout 15 ثانية لكل تبادل، والحد الإجمالي للعملية 45 ثانية. الاتصالات الخارجية لا تتبع redirects وتستخدم `trust_env=False` وعناوين DNS عامة مثبتة مع Host/SNI الأصليين.
- retry آلي بحد أقصى 8 محاولات وbackoff أُسّي حتى 6 ساعات؛ retry اليدوي متاح للأحداث `dead` فقط ويحافظ على عداد المحاولات. timestamps تتقدم عند إعادة المحاولة. تبقى دلالة التسليم **at-least-once**؛ لا يوجد exactly-once.
- الاختبارات الحالية تثبت ترتيب re-grade في السيناريوهات المختبرة، ومنع عامل ثانٍ على جلسة PostgreSQL مستقلة أثناء وجود lease، وإرسال الدرجة الأحدث بعد تحريره. لكنها لا تغلق معايير Issue [#155](https://github.com/HVA09/lumen-learning-platform/issues/155): لا يوجد اختبار مباشر لانتهاء lease ثم reclaim، ولا stale-owner finalization بعد انتقال الملكية، ولا محاكاة تثبت أن LMS قبل الدرجة ثم ضاع الرد، ولا اختبار ضغط يثبت عدم استنزاف DB pool عبر أهداف متعددة. اختبار timeout الحالي يرفع استثناءً اصطناعيًا ولا يثبت قبول LMS قبل فقدان الرد؛ كما أن اختبار timestamp يعطل `db_session.rollback` ليتوافق مع fixture، لذلك لا يُعد وحده إثباتًا لمسار rollback الحقيقي.
- صلاحيات إدارة المنصات والـmapping وسجل الدرجات وmanual retry محمية بـ `require_admin`. مخطط استجابة سجل الدرجات لا يعرض subject أو score أو comment أو raw lineitem أو OAuth material؛ والأخطاء المحفوظة عامة ومنقحة. تحقق SSRF يرفض العناوين غير العامة، يثبت DNS إلى عنوان عام، ويمنع redirects. قيد التوافق المفتوح: lineitem يجب أن يشارك token endpoint نفس الـorigin؛ يلزم إثبات ذلك مع كل LMS قبل توسيعه.
- لا تتوفر في سياق هذا التنفيذ بيانات اعتماد/tenants لـ Moodle Sandbox أو Canvas Sandbox؛ لم تُخمن إعدادات ولم يُجر اتصال بمنصة مجهولة. تبقى اختبارات registration وOIDC وresource-link mapping وOAuth وGradebook passback وre-grade وretry/timeouts وduplicate/uncertain delivery والحالات السلبية بوابتين منفصلتين مفتوحتين.
- الحالة: PR #154 **Open + Draft + Unmerged**؛ base/main عند `5a065c00ff739c21cad06d551c7e3aa51a3d604b`. لا دمج ولا تحويل إلى Ready for review قبل إغلاق فجوات Issue #155 ونجاح Sandbox على Moodle وCanvas كلٌّ على حدة.


---

## تحديث هندسي مؤكد — PR #154 — 2026-11-15 — CI 43755203129

- الرأس المفحوص: `555b3033c56ef7b86fda52fdae9db11c5fe02707` على `feat/lti-ags-rebased-20261115`؛ [CI #43755203129](https://github.com/HVA09/lumen-learning-platform/actions/runs/43755203129) اكتمل **4/4 Success**: Backend، Frontend tests/build، Browser E2E، وFull-history secret scan.
- Backend: **517 passed، 12 warnings، 89% coverage** على Python 3.12. فحوص migration/downgrade وPostgreSQL backup/restore على قواعد مؤقتة نجحت؛ لا يثبت ذلك تنفيذًا أو ترحيلًا على الإنتاج.
- المقارنة مع `main` عند `5a065c00ff739c21cad06d551c7e3aa51a3d604b`: **28 commits ahead / 0 behind**؛ 29 ملفًا متغيرًا. PR #154 ما زال Open + Draft + Unmerged.
- أضيفت في `backend/tests/test_lti_grade_target_binding.py` اختبارات PostgreSQL مستقلة تغطي الآن نقاط Issue #155 التي كانت موثقة سابقًا كفجوات: استعادة lease بعد expiry مع منع stale owner من finalization، محاكاة قبول LMS ثم فقدان الرد وإعادة المحاولة مع timestamp أحدث، و6 عمليات تسليم متزامنة لأهداف مختلفة مع التحقق من عدم وجود checked-out DB connections أثناء I/O. كما توجد اختبارات ترتيب re-grade ومنع العامل الثاني لنفس target قبل تحرير lease. CI على هذا الرأس اجتاز الاختبارات؛ Issue #155 نفسه ما زال مفتوحًا ولم يُغلق.
- حدود الإثبات: اختبار lease expiry يحاكي استئناف العامل القديم بعد takeover ولا يثبت منع أثر HTTP قديم إذا ظل طلب خارجي حيًا بعد انتهاء lease. يظل النظام **at-least-once**؛ لا exactly-once، وقد تتكرر الدرجة إذا قبلها LMS ثم ضاع الرد أو تعطل العامل قبل حفظ النجاح.
- مراجعة migration 0027: جدول lease بمفتاح فريد `(assignment_link_id, subject_hash)`، FK إلى assignment link بـ `ON DELETE CASCADE`، FK إلى grade event بـ `ON DELETE SET NULL`، وفهرس `locked_until`. downgrade يحذف الفهرس ثم الجدول. لا backfill في migration. فحوص CI اختبرت migrations/downgrade على بيئة مؤقتة فقط.
- مراجعة الخدمة: حجز ذري مشروط بانتهاء lease، owner token عشوائي 32 hex، COMMIT قبل OAuth/HTTP، ومعاملة قصيرة ثانية للتحقق من المالك وتسجيل النتيجة. DNS timeout 10s، HTTP timeout 15s لكل تبادل، إجمالي AGS timeout 45s، lease 120s؛ لا redirects، `trust_env=False`، DNS pinning لعناوين عامة مع Host/SNI الأصليين. لا يظهر في القراءة الساكنة عيب واضح يبرر تغييرًا برمجيًا إضافيًا في هذا الرأس.
- صلاحيات إدارة المنصات والموارد والروابط وسجل الدرجات وmanual retry محمية بـ `require_admin`. استجابة سجل الأحداث لا تعرض subject أو score أو raw lineitem أو OAuth material؛ رسائل الخطأ المخزنة عامة ومنقحة. OIDC state/nonce وissuer/audience/azp/deployment/target/resource claims يجري التحقق منها، وتُجلب مفاتيح JWKS دون redirects وبحد حجم.
- قيد توافق ما زال يحتاج اختبار LMS حقيقي: lineitem URL يشترط أن يطابق origin الخاص بـ OAuth token endpoint؛ قد لا يناسب كل إعدادات الاستضافة المنفصلة لدى LMS.
- بوابتان خارجيتان لم تُغلقا: لا توجد بيانات اعتماد/tenants متاحة لـ **Moodle Sandbox** أو **Canvas Sandbox** في هذا التنفيذ؛ لم تُخمن إعدادات ولم تُجر اختبارات فعلية. يجب اختبار كل منصة منفصلة: registration، OIDC launch، resource-link discovery/mapping، OAuth، Gradebook passback، re-grade، retry/timeouts، duplicate/uncertain delivery، والحالات السلبية.
- القرار: لا دمج ولا تحويل من Draft إلى Ready for review قبل اختبار Moodle وCanvas Sandbox فعليًا وتوثيق النتائج لكل منصة. لا تغييرات على main أو الإنتاج أو الأسرار أو الاستضافة أو بيانات الطلاب.


---

## تحديث استمرارية مؤكد — PR #154 — 2026-11-15 — CI 43755664314

- الرأس الذي أُعيد التحقق منه: `e8eb3e40d94f8793e1a74d21ea4f34809570704e` على `feat/lti-ags-rebased-20261115`. هذا الرأس توثيقي فوق شجرة الكود التي اجتازت CI على `555b3033c56ef7b86fda52fdae9db11c5fe02707`.

- أُضيف هذا السجل في commit d05988b1181a35d4cab5d9103c1a765601158ea1؛ [CI #43756286454](https://github.com/HVA09/lumen-learning-platform/actions/runs/43756286454) اكتمل 4/4 Success على هذا التحديث التوثيقي، وBackend 517 passed / 12 warnings / 89% coverage.
- [CI #43755664314](https://github.com/HVA09/lumen-learning-platform/actions/runs/43755664314) اكتمل **4/4 Success** على الرأس `e8eb3e4`: Backend، Frontend tests/production build، Browser E2E، وFull-history secret scan.
- Backend على Python 3.12: **517 passed، 12 warnings، 89% coverage**. فحوص migration/downgrade وPostgreSQL backup/restore نفذت على قواعد مؤقتة فقط؛ لا يعني ذلك أي ترحيل أو تعديل إنتاجي.
- المقارنة مع `main` عند `5a065c00ff739c21cad06d551c7e3aa51a3d604b`: **29 commits ahead / 0 behind**، و29 ملفًا متغيرًا. PR #154 ما زال **Open + Draft + Unmerged**.
- Issue [#155](https://github.com/HVA09/lumen-learning-platform/issues/155) أصبح **Closed** في 2026-11-15. تعليق الإغلاق يربط استيفاء معايير lease/DB/ordering باختبارات PostgreSQL على الرأس `555b3033c56ef7b86fda52fdae9db11c5fe02707` وCI [#43755203129](https://github.com/HVA09/lumen-learning-platform/actions/runs/43755203129): استعادة lease بعد expiry مع stale-owner fencing، محاكاة قبول LMS ثم فقدان الرد وإعادة المحاولة مع timestamp متزايد، وستة أهداف متزامنة دون اتصالات DB محجوزة أثناء I/O. إغلاق Issue #155 لا يغلق بوابتي Moodle وCanvas Sandbox.
- مراجعة migration 0027_lti_ags_delivery_lease: قيد unique على العمودين assignment_link_id وsubject_hash؛ FK إلى assignment link مع ON DELETE CASCADE، وFK إلى grade event مع ON DELETE SET NULL، وفهرس locked_until. لا backfill؛ downgrade يحذف الفهرس ثم الجدول. التحقق كان على PostgreSQL مؤقت في CI، وليس الإنتاج.
- مراجعة dispatch: upsert ذري لا يستولي على lease إلا إذا انتهت/فرغت، وowner token عشوائي 32 hex؛ COMMIT قبل OAuth/HTTP، ثم معاملة قصيرة بعد الشبكة تتحقق من owner token قبل finalization وتحرير lease. DNS timeout 10s، HTTP timeout 15s لكل تبادل، إجمالي 45s، lease 120s، مع منع redirects و`trust_env=False` وتثبيت DNS على عناوين عامة مع Host/SNI الأصليين.
- ترتيب re-grade: قفل submission يرفع `grade_version` ويضمن timestamps متزايدة؛ lease يسلسل الإرسال للـresource/learner نفسه، والأحداث الأقدم غير المرسلة تُعلّم superseded إذا وجدت نسخة أحدث قبل الحجز. الدلالة تظل **at-least-once** وليست exactly-once. stale-owner fencing يمنع العامل القديم من تعديل حالة DB بعد takeover، لكنه لا يستطيع إلغاء side effect خارجي إذا ظل طلب HTTP قديم حيًا خارج حدود المهلة أو قُبل لدى LMS؛ تبقى هذه مخاطرة تسليم موزع يجب مراقبتها في Sandbox.
- صلاحيات تسجيل/عرض المنصات والموارد والروابط وسجل الدرجات وmanual retry محمية بـ `require_admin`. مخطط سجل الأحداث لا يعرض subject أو score أو comment أو raw lineitem أو OAuth material، و`last_error` يحفظ نوع الاستثناء ورسالة عامة فقط. مع ذلك، يبقى `lti_subject` الخام محفوظًا في event/session/submission لأغراض الربط والتسليم؛ لم تُثبت في هذه المراجعة سياسة احتفاظ أو حذف/تشفير على مستوى الحقول. كما أن task warning الذي فُحص يسجل event ID فقط، ولم تكن هذه مراجعة شاملة لكل إعدادات logging.
- قيد توافق مفتوح: lineitem URL يجب أن يشارك origin الخاص بـ OAuth token endpoint. لا توسّع هذا القيد قبل إثباته على Moodle وCanvas.
- مانع خارجي: لم تتوفر ضمن سياق التنفيذ بيانات اعتماد أو tenants لـ **Moodle Sandbox** أو **Canvas Sandbox**؛ لم تُخمن إعدادات ولم يُجر اتصال بمنصة غير معروفة. يلزم لكل منصة على حدة اختبار registration، OIDC launch، resource-link discovery/mapping، OAuth، Gradebook passback، re-grade، retry/timeouts، duplicate/uncertain delivery، والحالات السلبية.
- لا دمج ولا تحويل من Draft إلى Ready for review قبل اكتمال Sandbox لكل منصة وتوثيق النتائج. لم تتغير `main` أو قواعد بيانات منشورة أو hosting أو secrets أو مفاتيح LMS أو بيانات طلاب.
