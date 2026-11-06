# دليل استمرارية المشروع عبر الأجهزة والمحادثات

آخر تحديث: 2026-11-06

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
- PR #141: animation/failure paths؛ CI #42265153710 نجح 4/4، وتم الدمج عند `1f76de769a224fb01c5ac66e9bccede331650dac`. main CI بعد الدمج #42265976307 كان قيد التنفيذ عند آخر تحقق.
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
