# الحالة التنفيذية لمشروع Lumen Learning Platform

آخر تحقق: **2026-11-06**.

> هذه الوثيقة هي نقطة الاستئناف المعتمدة. تحقّق دائمًا من أحدث commit وGitHub Actions قبل أي تغيير؛ لا تعتمد على تواريخ المحادثات أو حالة قديمة.

## الملخص التنفيذي

- المستودع: [HVA09/lumen-learning-platform](https://github.com/HVA09/lumen-learning-platform) — عام.
- الفرع الأساسي: `main`.
- آخر تغيير اختبار/جودة مدمج على `main`: PR #119 عند `f1d5884b8ee0a4c05a1be596502a969018bfcbe0`؛ أضاف خط أساس Frontend V8 report-only واختبارات مركزة للـ API adapters والملفات والإدارة والمحتوى. أحدث خط أساس Backend هو 90% مع 480 اختبارًا ناجحًا عبر CI PR #117/#119. لا توجد عتبة تغطية مفروضة ولا نشر إنتاجي مثبت.
- PR #95 مدمج عند `80be944a39ffd683daa4ee24cabe48a3bd9067c7`: يعيد تهيئة جلسة المتصفح عند عودة الشبكة، ويمنع retry غير الضروري بعد login/logout. CI على PR #42108841308 وبعد الدمج #42113922307 نجحا 4/4.
- PR #100 مدمج في `main` عبر Squash commit `2f77979fc735ea69690474bed60fce8a0c206fc7`. خط أساس Backend report-only: **431 passed, 20 warnings, 89% coverage** على رأس PR #100؛ لا يوجد حد أدنى مفروض، ولا تغيير في runtime أو API/DB/migrations أو إعدادات الإنتاج.
- PR #4 و#29–#46 و#48 و#49 و#51–#54 و#56–#59 و#62 و#64–#84 و#87 و#88 و#89 و#91 مدمجة، بما فيها PR #68 و#69 و#76 و#83 التوثيقية وPR #70/#73/#75/#77/#80/#81/#82/#84 لتوسيع Browser E2E. PR #87 أضاف إعادة الاتصال واختبار تعدد جلسات الإشعارات؛ PR #88 أضاف اختبار رسوب البوابة دون الحد وحفظ المحاولة ومهلة إعادة المحاولة. PR #55 و#86 مغلقان دون دمج. PR #59/#62/#64 خفّضت التحميل الأولي، و#65 أضاف Vite preload recovery، و#67 خفّض precache إلى 8 entries/378.63 KiB.
- PR #30 دُمج في 2026-11-03. بقي المسار القديم `app.services.quiz_logic` كواجهة توافق.
- CI #526 نجح على رأس PR #30، وCI #532 على PR #31، وCI #534 على PR #32؛ جميع وظائف Backend وFrontend/build وFull Git history secret scan نجحت.
- CI #537 نجح على main قبل PR #34: Backend **404 passed** وFrontend **51 passed**.
- CI #539 نجح على main بعد PR #34: Backend **405 passed** وFrontend **51 passed**.
- CI #541 نجح على main بعد PR #35: Backend **407 passed** وFrontend **51 passed**.
- CI #543 نجح على main بعد PR #36: Backend **407 passed** وFrontend **51 passed**.
- CI بعد PR #54: [#41759458975](https://github.com/HVA09/lumen-learning-platform/actions/runs/41759458975) نجح بالكامل على `7f6953636241997156e478a5ec489159825a7d2f`.
- CI بعد PR #57: [#41767787126](https://github.com/HVA09/lumen-learning-platform/actions/runs/41767787126) نجح بالكامل على `96fff938fa5ec85b921de247bfe7a3dbe3300071`.
- PR #58 (تحديث توثيقي) دُمج عند `92315de7ee18acdd2b44f5d473b9c1eef0ff7683`؛ CI بعد الدمج [#41850447579](https://github.com/HVA09/lumen-learning-platform/actions/runs/41850447579) نجح.
- PR #59 دُمج عند `30d768932934fb7c57e5f18da673de169e1bb6f2`؛ PR CI [#41850891816](https://github.com/HVA09/lumen-learning-platform/actions/runs/41850891816) وmain CI بعد الدمج [#41851527075](https://github.com/HVA09/lumen-learning-platform/actions/runs/41851527075) نجحا بالكامل: Backend **423 passed, 20 warnings**، Ruff **0 diagnostics**، Frontend **73 passed عبر 14 ملفًا**، production build وGitleaks وفحوص PostgreSQL وmigrations وRestic نجحت.
- PR #62 (تحميل MathText وKaTeX عند الحاجة) دُمج عند `6b53686ae3824d020243dd33115cc0bf81bd3c03`؛ PR CI [#41855423230](https://github.com/HVA09/lumen-learning-platform/actions/runs/41855423230) وmain CI بعد الدمج [#41856247148](https://github.com/HVA09/lumen-learning-platform/actions/runs/41856247148) نجحا بالكامل: Backend **423 passed, 20 warnings**، Ruff **0 diagnostics**، Frontend **73 passed عبر 14 ملفًا**، production build وGitleaks وفحوص PostgreSQL/backup/restore ناجحة.
- PR #64 (تحميل الاختبارات والمختبر والمحاكاة عند الطلب) دُمج عند `09d2a706236b4f9be55f3d8c66d461fee34f70c1`؛ PR CI [#41857581931](https://github.com/HVA09/lumen-learning-platform/actions/runs/41857581931) وmain CI بعد الدمج [#41858290575](https://github.com/HVA09/lumen-learning-platform/actions/runs/41858290575) نجحا بالكامل: Backend **423 passed, 20 warnings**، Ruff **0 diagnostics**، Frontend **74 passed عبر 14 ملفًا**، production build وGitleaks وmigrations وPostgreSQL backup/restore ناجحة.
- PR #65 (استعادة أخطاء تحميل الوحدات المؤجلة) دُمج عند `ee74aaa1136c471fb4b22b61247528e1ad7478c3`؛ PR CI [#41860852718](https://github.com/HVA09/lumen-learning-platform/actions/runs/41860852718) نجح بالكامل: Backend **423 passed, 20 warnings**، Ruff **0 diagnostics**، Frontend **80 passed عبر 16 ملفًا**، production build وGitleaks ناجحان. CI بعد الدمج على main [#41861598602](https://github.com/HVA09/lumen-learning-platform/actions/runs/41861598602) نجح بالكامل: Backend **423 passed, 20 warnings**، Ruff **0 diagnostics**، Frontend **80 passed عبر 16 ملفًا**، production build وGitleaks وmigrations وPostgreSQL backup/restore ناجحة.
- PR #67 (تقليل PWA precache وتحميل feature chunks عند الطلب) دُمج عند `2453b9124fc4eaa617aa5bb5493ebc0cf1400c9a`. Workbox precache أصبح **8 entries / 378.63 KiB** بدل **35 / 1328.16 KiB** (انخفاض 71.5%). اكتمل CI بعد الدمج لاحقًا ضمن تشغيل `main` [#41903896915](https://github.com/HVA09/lumen-learning-platform/actions/runs/41903896915) بنجاح كامل؛ لا توجد حاجة لإبقاء حالة #41886648386 القديمة بوصفها آخر تحقق.
- لا يوجد نشر إنتاجي مثبت.

## حالة المراحل

| المرحلة | الحالة | الدليل / المخرج |
|---|---|---|
| P0 — تثبيت خط الأساس | مكتمل | PR #4 و#29 مدمجان؛ CI #525 نجح على خط الأساس السابق لـ P1 |
| P1 — استخراج منطق Assessments | مكتمل | PR #30 مدمج، وCI #526 و#527 ناجحان |
| P2 — خريطة حدود المجالات والاعتماديات | مكتمل توثيقيًا | توثيق الاعتماديات والملكية الأولية في `ARCHITECTURE_PLAN.md` وADR-017؛ لا نقل إضافي قبل قرار مستقل |
| P3 — تجربة Backend ثانية صغيرة | مكتمل | PR #32 مدمج؛ CI #534 على PR وCI #535 على main نجحا |
| P4 — فصل حدود خدمات Backend | منفذ جزئيًا | PR #34/#35 (Learning Progress)، و#37 (Review/SRS)، و#40 (Gamification scoring) مدمجة؛ تبقى فرص فصل أخرى حسب تحليل الاعتماديات |
| P5 — تنظيم Frontend | P5.1–P5.4 مكتملة | PR #41 WebSocket، و#43 Session، و#44 Notifications state، و#46 نقلت ميزة الإشعارات إلى `features/notifications`؛ PR #42 وثّق الخريطة والخطة |
| P6 — الجودة والأداء والمراقبة | P6.0/P6.1 وP6.5 منفذة؛ P6.6 يغطي التدفقات الأساسية حتى PR #97. PR #100 يقيس Backend: **89%، 431 passed**؛ CI #42223767240 نجح 4/4 على رأس الوثائق. PR #102 يقيس Frontend: **31.80% statements، 91 passed عبر 17 ملفًا**؛ CI #42207211737 نجح 4/4. PR #101 يضيف اختبارات SMTP: **437 Backend passed** و`email_service.py` عند **92%**؛ CI #42126717163 نجح 4/4، والـ PR متسلسل فوق #100. PR #103 يضيف اختبارات auth/files/quiz/users API adapters؛ على الرأس `c718004` نجح Frontend **112/112** والبناء وفحص الأسرار الكامل، بينما Backend وBrowser E2E ما زالا قيد التنفيذ في CI #42224962672. بقي إعادة قياس التغطية بعد دمج الأدوات والاختبارات، اختبارات LTI/OIDC وFiles/ClamAV، RUM/Core Web Vitals، Typecheck وقياسات الهاتف. جميع PRs المذكورة مفتوحة وغير مدمجة.
| P7 — الإطلاق | غير جاهز | بوابات الاستضافة والتشغيل أدناه لم تُغلق |

## آخر نقاط التحقق
- PR #89: [CI #42101543986](https://github.com/HVA09/lumen-learning-platform/actions/runs/42101543986) نجح 4/4 على رأس الفرع المحدّث `515dca92e3bb11afd341dacec637307832ad55fc`: Backend tests، Frontend tests/build، Browser E2E، وFull Git history secret scan. دُمج عبر Squash في `main` عند `06a66e0e70dd2e929ab7a818ad65a96db11465a3`. CI بعد الدمج [#42102276661](https://github.com/HVA09/lumen-learning-platform/actions/runs/42102276661) اكتمل بنجاح 4/4.

- [CI #41953273414](https://github.com/HVA09/lumen-learning-platform/actions/runs/41953273414): نجح على PR #84 عند `96b3ea34183553b491ccdb1ff69c473e79302978` بالوظائف الأربع. وظيفة Browser E2E اتصلت بخدمة `clamav/clamav:1.4.6` مؤقتة، قبلت ملف CSV نظيفًا، ورفضت EICAR بـ HTTP 422، وتحققت من عدم بقاء الملف أو سجل FileAttachment للعينة المرفوضة. نجح Frontend tests/build وBackend suite وGitleaks full-history أيضًا.
- CI بعد دمج PR #84 على main [#41954300369](https://github.com/HVA09/lumen-learning-platform/actions/runs/41954300369) نجح بالكامل 4/4: Backend **423 passed, 20 warnings**؛ Ruff **0 diagnostics**؛ Frontend **80 passed عبر 16 ملف اختبار**؛ production audit **0 vulnerabilities**؛ full dependency audit **2 Low و4 Moderate وصفر High/Critical**؛ Browser E2E وGitleaks full-history وmigrations وPostgreSQL backup/restore نجحت.
- [CI #41925605855](https://github.com/HVA09/lumen-learning-platform/actions/runs/41925605855): نجح على رأس PR #75 `87e3778b581e4a04e275024defa080b194e0ba62` بالوظائف الأربع؛ Browser E2E أثبت بدء Quiz تدريبي وتسليم محاولة بلا إجابات، عدم كشف مفاتيح الإجابة في استجابة البدء، إرجاع تصحيح وتغذية راجعة من الخادم، وظهور المحاولة ودرجتها في سجل الخادم بعد reload.
- [CI #41938791393](https://github.com/HVA09/lumen-learning-platform/actions/runs/41938791393): نجح بعد دمج PR #75 على `main` عند commit `1c94e4f73695b675d8929daf25b35c8d718aac5d`؛ الوظائف الأربع نجحت. Backend **423 passed, 20 warnings**؛ Frontend **80 passed عبر 16 ملفًا**؛ Ruff **0 diagnostics**؛ production audit **0 vulnerabilities**؛ full dependency audit **2 Low و4 Moderate، وصفر High/Critical**؛ Browser E2E وGitleaks full-history نجحا.
- [CI #41940578786](https://github.com/HVA09/lumen-learning-platform/actions/runs/41940578786): نجح على رأس PR #77 `b71abeca28cdfd8da8e2f43c6c3f3010ae636b60` بالوظائف الأربع؛ Browser E2E أثبت إخفاء أزرار الإدارة والمحتوى عن الطالب، صلاحيات المعلم وإدارة المحتوى، حصر كل معلم على فصله ورفض الوصول إلى فصل المعلم الآخر، وصلاحيات المسؤول.
- [CI #41941142454](https://github.com/HVA09/lumen-learning-platform/actions/runs/41941142454): نجح بعد دمج PR #77 على `main` عند `451572c1253351e0b4406ed21480b659b2862406`؛ Backend وFrontend/build وBrowser E2E وGitleaks full-history كلها نجحت.
- CI #41947786739: نجح بعد دمج PR #80 على main عند commit d1eb01ee45b197f4dc680adf17ac7611b1365f46؛ الوظائف الأربع نجحت، واختبار المتصفح أثبت إنشاء درس غير منشور ثم نشره ورؤيته من حساب الطالب.
- CI #41949251573: نجح بعد دمج PR #81 على main عند commit 3315c020980d732c51df95ddcfb4bcf0d54d909d؛ الوظائف الأربع نجحت، بما فيها Browser E2E الذي تحقق من نتيجة Quiz المحسوبة على الخادم عند عتبة اجتياز البوابة.
- CI #41949826358: نجح على رأس PR #82 7b42ff9ba5b0338bbc7fa8d3888f459605c36dbe بالوظائف الأربع؛ Browser E2E أثبت إنشاء سؤال اختيار متعدد وتعديله وتعطيله وحذفه من واجهة المعلم.
- CI بعد دمج PR #82 على main [#41950657568](https://github.com/HVA09/lumen-learning-platform/actions/runs/41950657568) نجح 4/4 على commit cf15149abe546627ee36feba65fcf48dbab3ba64: Backend 423 passed و20 warnings؛ Ruff 0 diagnostics؛ Frontend 80 passed عبر 16 ملفًا؛ production audit 0 vulnerabilities؛ full dependency audit 2 Low و4 Moderate وصفر High/Critical؛ Browser E2E وGitleaks وmigrations وPostgreSQL backup/restore نجحت.

- [CI #41919944969](https://github.com/HVA09/lumen-learning-platform/actions/runs/41919944969): نجح على رأس PR #73 `1f929c6403a59cc4154999f42d4c9f784124b963` قبل الدمج. Backend **423 passed, 20 warnings**؛ Frontend **80 passed عبر 16 ملفًا**؛ Playwright أثبت إكمال الدرس واستعادة `completed=true` بعد reload؛ Ruff **0 diagnostics**؛ production audit **0 vulnerabilities**؛ full dependency audit **2 Low و4 Moderate**؛ Gitleaks full-history نجح.
- [CI #41920779594](https://github.com/HVA09/lumen-learning-platform/actions/runs/41920779594): تحقق ما بعد دمج PR #73 على `main` عند commit `2d8721efbd581952cb16c3b6d64904a6ef5f6256`؛ الوظائف الأربع نجحت. Backend **423 passed, 20 warnings**، Frontend **80 passed عبر 16 ملفًا**، Browser E2E أثبت إكمال الدرس واستمرار التقدم بعد reload، Ruff **0 diagnostics**، production audit **0 vulnerabilities**، full dependency audit **2 Low و4 Moderate**، وGitleaks full-history نجح.

- [CI #525](https://github.com/HVA09/lumen-learning-platform/actions/runs/41648785991): نجح على خط الأساس `44308dfbc01e1c9a85a8cb5b77c3d18ecdebd78a` قبل PR #30؛ شمل 402 اختبار Backend، و51 اختبار Frontend، وبناء الإنتاج، وفحص Git history الكامل، وفحوصات Compose وmigrations وbackup/restore.
- [CI #526](https://github.com/HVA09/lumen-learning-platform/actions/runs/41651497742): نجح على رأس PR #30 `7e87b7f5fb64be38d45402d47b9efd2196a66bc0`؛ جميع الوظائف الثلاث نجحت.
- [CI #527](https://github.com/HVA09/lumen-learning-platform/actions/runs/41658136856): نجح على commit PR #30.
- [CI #532](https://github.com/HVA09/lumen-learning-platform/actions/runs/41659564175): نجح على PR #31.
- [CI #534](https://github.com/HVA09/lumen-learning-platform/actions/runs/41661359094): نجح على PR #32، بما في ذلك 404 اختبار Backend و51 اختبار Frontend.
- [CI #535](https://github.com/HVA09/lumen-learning-platform/actions/runs/41671140458): نجح على main بعد PR #32.
- [CI #536](https://github.com/HVA09/lumen-learning-platform/actions/runs/41672070138): نجح على PR #33.
- [CI #537](https://github.com/HVA09/lumen-learning-platform/actions/runs/41672915529): نجح على main قبل PR #34.
- [CI #538](https://github.com/HVA09/lumen-learning-platform/actions/runs/41675092421): نجح على PR #34؛ 405 اختبارات Backend و51 Frontend.
- [CI #539](https://github.com/HVA09/lumen-learning-platform/actions/runs/41675793048): نجح بالكامل على main بعد PR #34؛ 405 Backend و51 Frontend.
- [CI #540](https://github.com/HVA09/lumen-learning-platform/actions/runs/41677067045): نجح على PR #35؛ 407 Backend و51 Frontend.
- [CI #541](https://github.com/HVA09/lumen-learning-platform/actions/runs/41677706751): نجح على main بعد PR #35؛ 407 Backend و51 Frontend.
- [CI #543](https://github.com/HVA09/lumen-learning-platform/actions/runs/41679570211): نجح على main بعد PR #36؛ 407 Backend و51 Frontend.
- [CI #544](https://github.com/HVA09/lumen-learning-platform/actions/runs/41687074194): نجح على PR #37؛ 417 Backend و51 Frontend.
- [CI #545](https://github.com/HVA09/lumen-learning-platform/actions/runs/41687829625): نجاح تاريخي على `de79d3e4` قبل PR #39.
- [CI #41738385373](https://github.com/HVA09/lumen-learning-platform/actions/runs/41738385373): نجح على `main` بعد PR #44.
- [CI #41738681026](https://github.com/HVA09/lumen-learning-platform/actions/runs/41738681026): نجح على رأس PR #39 بعد إعادة تأسيسه؛ إصلاح Compose اجتاز فحصًا مخصصًا.
- [CI #41743356088](https://github.com/HVA09/lumen-learning-platform/actions/runs/41743356088): نجح على PR #42 بعد تحديث وثائق معمارية الواجهة والخطة.
- [PR #42](https://github.com/HVA09/lumen-learning-platform/pull/42) دُمج في `main` بالـ commit `aaeeb38e0b16c0ee2d2cea3664a6a3b6b00e1eac`؛ [CI بعد الدمج #41744012439](https://github.com/HVA09/lumen-learning-platform/actions/runs/41744012439) نجح بالكامل.
- [CI #41742892283](https://github.com/HVA09/lumen-learning-platform/actions/runs/41742892283): نجح على `main` بعد PR #39.
- [CI #41744012439](https://github.com/HVA09/lumen-learning-platform/actions/runs/41744012439): نجح على `main` بعد PR #42.
- [CI #41744744642](https://github.com/HVA09/lumen-learning-platform/actions/runs/41744744642): نجحت جميع وظائف Backend وFrontend/build وGitleaks على PR #46 قبل الدمج.
- [PR #46](https://github.com/HVA09/lumen-learning-platform/pull/46) دُمج عبر squash commit `ee149a40b144883b0fea34232ae730574d5e5ed7`؛ [CI بعد الدمج #41745646366](https://github.com/HVA09/lumen-learning-platform/actions/runs/41745646366) نجح بالكامل على `main`.
- [PR #49](https://github.com/HVA09/lumen-learning-platform/pull/49) أضاف Ruff 0.17.3 بوضع report-only؛ [CI على PR #49](https://github.com/HVA09/lumen-learning-platform/actions/runs/41750390626) و[main #41754238271](https://github.com/HVA09/lumen-learning-platform/actions/runs/41754238271) نجحا.
- [PR #51](https://github.com/HVA09/lumen-learning-platform/pull/51) حدّث سجلات المشروع بعد إضافة Ruff؛ PR CI #41755785196 وmain CI #41756353787 نجحا.
- [PR #52](https://github.com/HVA09/lumen-learning-platform/pull/52) جعل إعادة التصدير في أربع واجهات توافق صريحة؛ PR CI #41756512842 وmain CI #41756990109 نجحا.
- [PR #53](https://github.com/HVA09/lumen-learning-platform/pull/53) عالج بقية ملاحظات Ruff؛ CI #41757169187 نجح: Backend 423 passed و20 warnings، وFrontend 73 passed/14 files، وGitleaks ناجح. تقرير Ruff أصبح 0 diagnostic(s). تشغيل main بعد الدمج #41757735260 كان جارياً وقت التوثيق.

## ما تم إنجازه

- استيراد الواجهة والخلفية إلى المستودع وتوحيد خط الأساس عبر PR #4.
- تحسينات المصادقة والجلسات وCSRF وTOTP وتشفير أسرار TOTP وقواعد إنشاء المسؤول الأول.
- حماية مسارات رفع الملفات والتحقق من النوع والحجم وفحص البرمجيات الخبيثة باستخدام ClamAV مع حصص تخزين لكل مستخدم.
- إضافة idempotency لمعالجة Webhooks.
- إعداد اختبارات PostgreSQL للترحيلات والحفاظ على البيانات والنسخ الاحتياطي والاستعادة.
- إضافة مسار اختياري للنسخ الاحتياطي الخارجي المشفر باستخدام Restic؛ لم يتم إعداد مزود خارجي حقيقي بعد.
- تشغيل CI للواجهة والخلفية وفحص الأسرار في تاريخ Git الكامل.
- اعتماد Modular Monolith كاتجاه معماري، وتنفيذ وحدات Assessments وLearning Progress وReview/SRS وGamification النقية مع واجهات توافق عند الحاجة.
- استخراج دورة WebSocket إلى `useNotificationsSocket`، وإدارة الجلسة إلى `useSession`، وحالة الإشعارات والقراءات إلى `useNotifications` عبر PRs #41/#43/#44؛ ثم نقل API adapter وHook ومكون الجرس واختباراتها إلى `features/notifications` عبر PR #46؛ كلها مدمجة.
- إصلاح escaping لمتغير فترة النسخ الخارجي في Docker Compose مع assertion للـ rendered command عبر PR #39.

## الوضع المعماري الحالي

- Backend: FastAPI + PostgreSQL. ما زالت معظم المكونات منظمة أفقيًا في `auth/` و`routers/` و`models/` و`schemas/` و`services/`.
- Assessments: منطق التصحيح والتحقق والاختيار والإتقان في `app/modules/assessments/domain/quiz_logic.py`، ومنطق تحليل الأسئلة النقي في `app/modules/assessments/domain/question_analytics.py`. المساران القديمان في `app/services/` واجهتا توافق.
- Learning Progress: قاعدتا `compute_streak` و`topic_progress` في `app/modules/learning_progress/domain/` بعد PR #34 و#35، مع واجهات توافق. يبقى `study_activity.py` مسؤولًا عن التخزين، و`build_learning_path` جامعًا لبيانات Catalog وProgress داخل service.
- Review/SRS: انتقال SM-2+ النقي وEnum `CardState` في `app/modules/review/domain/sm2.py` بعد PR #37؛ يبقى `ReviewCard` في ORM والخدمة محولًا متوافقًا، وmigration 0010 دون تغيير.
- Frontend: React 19 + Vite. المكونات العامة ما زالت أساسًا في `src/components`، والعميل HTTP المشترك في `src/lib/api.js`. أصبحت الإشعارات أول ميزة منظمة داخل `src/features/notifications/` وتشمل API adapter وNotificationBell وHooks والاختبارات؛ بقي `useSession` و`useDirection` في `src/hooks`.
- يجب المحافظة على جلسات HttpOnly وCSRF، وعقود API الحالية، والعربية/الإنجليزية، وRTL/LTR، وتجربة الهاتف.
- سجل النماذج الصريح في `app/models/__init__.py` ضروري لاكتشاف Alembic؛ لا تنقل النماذج قبل خطة تسجيل واختبارات ترحيل.

## نتيجة مراجعة الاعتماديات الأولية لـ P2

- `question_analytics.py`: دوال نقية لتحليل الأسئلة نُقلت إلى `modules/assessments/domain` عبر PR #32؛ بقيت استعلامات SQL وتجميع استجابة API داخل `routers/content.py`.
- `learning_path.py`: `build_learning_path` منسق يجمع بيانات Catalog وProgress ويشكّل مسار الطالب؛ قواعد حالة الموضوع والتوصية منفصلة في Learning Progress domain عبر PR #35.
- `study_activity.py`: خدمة مرتبطة بقاعدة البيانات لقراءة وكتابة `StudyDay`؛ تستورد قاعدة حساب السلسلة من `modules/learning_progress/domain/streak_logic.py` عبر PR #34.
- `spaced_repetition.py`: بعد PR #37 أصبحت محول ORM إلى انتقال SM-2+ النقي في `modules/review/domain/sm2.py`؛ يحافظ على تعديل البطاقة نفسها، ولا يتغير enum أو migration 0010.
- `achievements.py`: خدمة استعلامات عابرة لمجالات الاختبارات والواجبات والدروس والبطاقات والتقدم؛ لا تنقلها ككتلة واحدة إلى مجال منفرد.
- `routers/content.py` يجمع إدارة الدروس والأسئلة وتحليلها؛ و`routers/assignments.py` يعتمد على عضوية الفصول؛ يجب احترام هذه العلاقات عند رسم الحدود.
- `app/models/__init__.py` يحمّل النماذج لتسجيلها لدى SQLAlchemy/Alembic.

هذه ملاحظات من قراءة الملفات والاستيرادات، وليست إعادة هيكلة منفذة.

## ما يمنع الإطلاق الإنتاجي

1. لم يتم اختيار واستيثاق مضيف إنتاجي مجاني مناسب لكل مكونات النظام، دون بطاقة أو رسوم غير مقصودة.
2. HTTPS والنطاق وشهادة TLS لم تُختبر على بيئة حقيقية.
3. SMTP فعلي مع TLS وأسرار المرسل غير مُعد.
4. ClamAV يحتاج اختبار موارد وتوفر على المضيف الحقيقي قبل تفعيل رفع الملفات إنتاجيًا.
5. LTI يحتاج إعادة تأسيس سلسلة PR #16–#23 على خط الأساس الجديد، ثم اختبار Moodle/Canvas sandbox.
6. Restic يحتاج وجهة تخزين خارجية حقيقية واختبار استعادة منها؛ نجاح CI الحالي يستخدم مستودعًا مؤقتًا.
7. مفاتيح وأسرار الإنتاج يجب إعدادها خارج Git وفي مدير أسرار مناسب.
8. لا يوجد نشر إنتاجي مثبت.

## قواعد العمل المعتمدة

- الميزانية الحالية صفر؛ لا تنشئ موارد قد تولّد فاتورة، ولا تعتمد استضافة تتطلب بطاقة قبل التحقق.
- لا تعدّل `main` مباشرة؛ استخدم فروعًا وطلبات دمج.
- لا تتجاوز حماية GitHub أو تزور موافقة. يمكن تخطي المراجعة البشرية الاختيارية فقط، لا الشروط الإلزامية التي يفرضها GitHub.
- لا تدمج سلسلة LTI القديمة مباشرة؛ أعد تأسيسها على main الحالي بالترتيب، وحل التعارضات مع اختبارات جديدة.
- لا تعتبر نجاح CI إثباتًا لتشغيل إنتاجي أو اختبار LMS حي أو مراجعة بشرية.
- لا تغيّر API أو قاعدة البيانات أو migrations ضمن نقل تنظيمي بحت.
- بعد كل مرحلة، حدّث هذه الوثيقة و`ARCHITECTURE_PLAN.md` و`DECISIONS.md` مع commit وروابط CI.

## الخطوة التالية

1. أولوية الاختبارات التالية: تدفقات التطبيق في `App.jsx`، بما فيها bootstrap للجلسة، انتهاء الجلسة، الصلاحيات، التنقل، وفتح الوحدات المؤجلة.
2. اختبر `LearningPath.jsx` و`LabPanel.jsx` والمحاكاة على مستوى قواعد التعلم والحسابات، لا العرض فقط.
3. أكمل RUM/Core Web Vitals بقياس فعلي على هاتف واتصال بطيء قبل وضع budgets رقمية.
4. أضف Typecheck وESLint تدريجيًا؛ ابدأ بتقرير تشخيصي ولا تفرض gate قبل مراجعة المخرجات.
5. P7 غير جاهزة: يلزم مضيف مجاني بلا بطاقة، HTTPS فعلي، اختبار SMTP حقيقي، تقييم موارد ClamAV على المضيف، أسرار إنتاج خارج Git، ووجهة Restic خارجية مع اختبار استعادة.

- لا يوجد نشر إنتاجي مثبت. الميزانية صفر؛ لا موارد مدفوعة أو دفع إلكتروني، ولا تعطيل لفحوص الأمن أو حماية GitHub.
## تحديث تحقق 2026-11-06 — استعادة الشبكة وقياس التغطية

هذا التحديث هو الأحدث، ويصحح أي سطر أقدم أدناه يقول إن PR #95 أو #97 ما زال مفتوحًا أو قيد التحقق.

- PR #95 مدمج في `main` عند `80be944a39ffd683daa4ee24cabe48a3bd9067c7`: إعادة محاولة تهيئة الجلسة بعد حدث `online`، مع منع التكرار وحماية login/logout. CI الخاص بالـ PR #42108841308 وبعد الدمج #42113922307 نجح 4/4.
- PR #97 مدمج في `main` عند `fc25ba75987403a85154e55fc70f329d38ee6371`: Browser E2E يتحقق من تعافي `GET /users/me` بعد Offline → Online وعودة لوحة المتعلم دون reload. CI الخاص بالـ PR #42114408046 وبعد الدمج #42115046453 نجح 4/4.
- PR #100 مدمج في `main` عبر `2f77979fc735ea69690474bed60fce8a0c206fc7`. أضاف قياس تغطية Backend report-only وسبعة اختبارات للمهام الخلفية؛ لا يغيّر منطق التطبيق أو API أو قاعدة البيانات أو إعدادات الإنتاج.
- تشغيل CI على رأس PR #100 [#42124352248](https://github.com/HVA09/lumen-learning-platform/actions/runs/42124352248) اكتمل بنجاح 4/4. Backend: **431 passed, 20 warnings**، زمن الاختبارات 183.07 ثانية، وتغطية Backend **89%** (4,375 statements / 410 missed / 942 branches / 142 partially covered). `app/tasks.py` ارتفعت من 37% إلى 92%.
- `pytest-cov==7.1.0` اعتماد تطوير فقط؛ لا يوجد حد تغطية أدنى مفروض حتى الآن. لا نرفع النسبة باختبارات شكلية أو باستثناء وحدات غير مغطاة.
- رأس `main` بعد الدمج هو `2f77979fc735ea69690474bed60fce8a0c206fc7`. تشغيل ما بعد الدمج [#42239814878](https://github.com/HVA09/lumen-learning-platform/actions/runs/42239814878) جارٍ عند إعداد هذا التحديث؛ نجحت وظائف Frontend/build وBrowser E2E وGitleaks، واختبارات Backend ما زالت قيد التنفيذ. لا يوجد نشر إنتاجي مثبت.

### الخطوات التالية

1. اختبارات SMTP fail-safe أُضيفت في PR #101، وبلغت `email_service.py` تغطية 92%؛ المتبقي اختبارات LTI/OIDC/JWKS/SSRF والملفات/ClamAV مع الحفاظ على عدم كشف الرموز والأسرار.
2. قياس Frontend أُضيف في PR #102 بإصدار provider مطابق لـ Vitest؛ لا توجد عتبة مفروضة. بعد دمج PRs #102 و#103 أعد قياس التغطية على مجموعة الاختبارات الموحّدة.
3. استكمال RUM/Core Web Vitals واختبار الأداء على هاتف واتصال بطيء عند توفر بيئة معاينة مناسبة.
4. استكمال متطلبات P7: استضافة مجانية مناسبة بلا بطاقة، HTTPS، SMTP، ClamAV على موارد المضيف، أسرار خارج Git، ووجهة نسخ احتياطي خارجية واختبار استعادة حقيقي.

## تحديث 2026-11-06 — خط أساس تغطية الواجهة

- آخر تغيير اختبار/جودة مدمج على `main` هو PR #100 عند `2f77979fc735ea69690474bed60fce8a0c206fc7`؛ آخر تغيير سلوكي بقي PR #97 عند `fc25ba75987403a85154e55fc70f329d38ee6371`. لا يوجد نشر إنتاجي مثبت.
- PR #100 مدمج في `main` عبر `2f77979fc735ea69690474bed60fce8a0c206fc7`: خط أساس Backend report-only؛ 431 اختبارًا ناجحًا و89% coverage على رأسه قبل الدمج، ونجح CI قبل الدمج 4/4.
- PR #102 على الفرع `chore/frontend-coverage-baseline` ورأسه `58dbf951d478705240e3e5746dee0546967d9e52`: أضاف V8 coverage report-only للواجهة. CI #42207211737 نجح 4/4؛ Frontend **91 passed عبر 17 ملف اختبار**، وتغطية **31.80% statements / 35.72% branches / 28.82% functions / 32.05% lines**. لا حد أدنى مفروض ولا تغيير runtime.
- PR #100 مدمج؛ PR #102 ما زال مفتوحًا وغير مدمج على سلسلة تغطية Frontend، ولا نتجاوز أي شرط مراجعة تفرضه حماية GitHub.
- أولويات الاختبار بعد القياس: Frontend API adapters، App/Admin/Content Manager/Files، ثم SMTP fail-safe وLTI/OIDC/JWKS/SSRF ومسارات الملفات/ClamAV. استخدم mocks وخدمات CI المؤقتة، ولا تفتح ClamAV على الإنترنت.
- تظل ميزانية المشروع صفرًا؛ لا موارد مدفوعة أو دفع إلكتروني، ولا نشر إنتاجي قبل استكمال شروط P7.



## توثيق استمرارية 2026-11-06 — دمج Backend coverage

- تم دمج PR #100 بطريقة Squash في `main` عند `2f77979fc735ea69690474bed60fce8a0c206fc7`؛ أضاف `pytest-cov==7.1.0` كاعتماد تطوير وسبعة اختبارات للمهام الخلفية مع تقرير coverage report-only. القياس السابق للدمج: 431 passed، 20 warnings، 89% coverage؛ لا يوجد threshold.
- تشغيل main CI بعد الدمج [#42239814878](https://github.com/HVA09/lumen-learning-platform/actions/runs/42239814878) كان قيد التنفيذ عند كتابة هذا التحديث؛ لا نسجل نجاحه قبل انتهائه.
- PR #105 على `test/files-clamav-fail-safe` عند `a104fdcff1505b85c0d4833e67c83d64c9f69c1f` أصلح عزل transaction لاختبار quota باستخدام SAVEPOINT؛ لا يغير كود التطبيق. CI [#42240006523](https://github.com/HVA09/lumen-learning-platform/actions/runs/42240006523) كان قيد التنفيذ. لا تدمجه قبل نجاح الوظائف الأربع.
- PR #108 نجح في تشغيل CI الثاني [#42233982927](https://github.com/HVA09/lumen-learning-platform/actions/runs/42233982927): Backend وFrontend/build وBrowser E2E وFull-history Gitleaks نجحت. ما زال مفتوحًا ومتسلسلًا فوق PR #107.
- PR #101 SMTP tests و#102 Frontend coverage و#103 API adapters و#104 LTI DNS/JWKS و#106 FilesPanel و#107 AdminDashboard ما زالت طلبات مفتوحة؛ راجع base/head لكل PR قبل أي retarget أو merge بعد دمج PR #100.
- لا يوجد نشر إنتاجي مثبت. الميزانية صفر، لا بطاقة ولا دفع، ولا تعطيل لفحوص الأمن أو CI.


## نقطة الاستئناف المعتمدة — 2026-11-06 بعد PR #119

> هذا الملحق أحدث من ملاحظات الحالة السابقة في هذه الوثيقة، ويُستخدم مرجعًا للحالة الحالية حتى تحديث لاحق.

- رأس `main` الحالي بعد PR #123: `53a1912773dbbaf4a854ec7d110dc4fd46a2b6a3`.
- PR #100 مدمج: Backend coverage report-only، 431 passed و89% على رأسه قبل التوسعات اللاحقة.
- PR #109 مدمج: تحديث توثيق الاستمرارية وخطة المشروع بعد دمج خط الأساس.
- PR #113 مدمج: اختبارات حصص الملفات وتنظيف الرفع وفشل ClamAV؛ CI #42241558869 نجح 4/4، وBackend 447 passed و21 warnings.
- PR #117 مدمج: اختبارات SMTP transport وLTI DNS/JWKS؛ CI #42242688194 نجح 4/4، وBackend 480 passed و21 warnings و90% coverage. تغطية الوحدات: `email_service.py` 92%، `lti_service.py` 89%، `malware_scanner.py` 93%، `routers/files.py` 82%، `tasks.py` 92%.
- PR #119 مدمج: V8 coverage report-only واختبارات API adapters وFilesPanel وAdminDashboard وContentManager؛ CI #42243595538 نجح 4/4. Frontend 142 tests عبر 24 ملفًا؛ statements 50.34%، branches 53.53%، functions 47.98%، lines 50.63%.
- CI بعد PR #117 على `main` [#42243421397](https://github.com/HVA09/lumen-learning-platform/actions/runs/42243421397) وCI بعد PR #119 [#42244364141](https://github.com/HVA09/lumen-learning-platform/actions/runs/42244364141) نجحا 4/4. PR #123 حذف import غير مستخدم فقط؛ CI الخاص به [#42244746449](https://github.com/HVA09/lumen-learning-platform/actions/runs/42244746449) نجح 4/4، وBackend 480 passed. تشغيل `main` بعد PR #123 [#42245438258](https://github.com/HVA09/lumen-learning-platform/actions/runs/42245438258) بدأ وما زال قيد التحقق عند كتابة هذا التحديث.
- التغييرات في PR #113 و#117 و#119 اختبارات/قياس جودة فقط؛ لم تغيّر سلوك التطبيق أو API أو DB أو migrations أو إعدادات الإنتاج. التغطية report-only ولا يوجد threshold.
- أُغلقت الطلبات المتداخلة/المكررة #101–#108 و#110–#112 و#114–#116 و#118 بعد نقل التغييرات إلى فروع نظيفة ودمج البدائل؛ PR #113 و#117 و#119 مدمجة.

### الخطوات التالية

1. الأولوية التالية اختبارات تركيب `App.jsx` وتدفقات الجلسة والأدوار والتنقل وفتح الوحدات؛ الملف ما زال 0% في تقرير الواجهة.
2. بعد ذلك اختبارات `LearningPath.jsx` و`LabPanel.jsx` ومحاكاة الدوائر/التفاضل/الدوال/المقذوفات، مع اختبار الحسابات والسلوك التعليمي لا العرض فقط.
3. استكمال RUM وCore Web Vitals بقياس ميداني على هاتف واتصال بطيء قبل وضع أهداف أداء رقمية.
4. Typecheck وESLint غير معتمدين كـ gates بعد؛ ابدأ بتقييم report-only ثم راجع التحذيرات قبل فرض حد.
5. لا تزال P7 غير جاهزة: نحتاج خيار استضافة مجانيًا بلا بطاقة، HTTPS فعليًا، اختبار SMTP حقيقي لاحقًا، قياس موارد ClamAV على المضيف، أسرار إنتاج خارج Git، ووجهة Restic خارجية مع استعادة حقيقية.

- لا يوجد نشر إنتاجي مثبت. الميزانية صفر؛ لا موارد مدفوعة أو دفع إلكتروني، ولا تعطيل لفحوص الأمن أو حماية GitHub.


## نقطة الاستئناف المعتمدة — 2026-11-06 بعد PR #141

- رأس `main`: `1f76de769a224fb01c5ac66e9bccede331650dac` بعد دمج PR #141.
- PR #129 دمج اختبار `useSession` تحت `React.StrictMode`؛ CI #42247388390 نجح 4/4.
- PR #133 دمج إعادة اتصال WebSocket فور عودة الشبكة؛ CI #42248648649 نجح 4/4.
- PR #136 دمج اختبارات `LearningPath` وتحسين الاعتمادية: فشل إحصاءات streak الاختيارية لا يحجب المنهج؛ CI #42250578866 نجح 4/4.
- PR #137 دمج اختبارات توجيه المحاكاة والتحميل الكسول في `LabPanel`؛ CI #42251617174 نجح 4/4.
- PR #138 حدّث خريطة معمارية الواجهة؛ CI #42252349059 نجح 4/4.
- PR #140 دمج اختبارات حسابات الرياضيات والفيزياء والدوائر وتحدي Python؛ CI #42253279488 نجح 4/4، وCI على main بعده #42254119108 نجح 4/4.
- PR #141 دمج اختبارات مسارات الإجابات الخاطئة وحركة المقذوف وأخطاء Pyodide وتنفيذ Python؛ CI على PR #42265153710 نجح 4/4. تشغيل main بعد الدمج #42265976307 اكتمل بنجاح 4/4 في [CI #42265976307](https://github.com/HVA09/lumen-learning-platform/actions/runs/42265976307).

### خط أساس Frontend بعد اختبارات P6

- 187 اختبارًا ناجحًا عبر 28 ملف اختبار في CI PR #141.
- Statements: **70.83%** (1,341/1,893).
- Branches: **65.26%** (682/1,045).
- Functions: **60.16%** (376/625).
- Lines: **71.85%** (1,261/1,755).
- أمثلة من الملفات: `App.jsx` 75% statements؛ `LearningPath.jsx` 100%؛ `LabPanel.jsx` 100%؛ `CircuitSim.jsx` 98.64%؛ `PythonLabSim.jsx` 78.57%.
- يظل قياس التغطية report-only ولا يوجد حد أدنى مفروض. اختبارات App تستخدم mocks لعزل orchestration، ولا تعني تغطية كل رحلة منتج حقيقية أو كل مكونات الواجهة.

### ما تبقى في P6 وP7

1. توسيع حالات `App.jsx` غير المغطاة واختبارات مكونات المحاكاة حسب المخاطر، لا بهدف رفع رقم التغطية وحده.
2. قياس RUM/Core Web Vitals ميدانيًا؛ لا توجد حاليًا حزمة `web-vitals` أو نقطة RUM مثبتة في الواجهة.
3. اختبار يدوي على هاتف فعلي واتصال ضعيف: تحميل App Shell، فتح وحدة lazy لأول مرة، استعادة الجلسة، WebSocket، ورفع ملف. لا نسجل هذا كمنجز قبل تنفيذ القياس على جهاز حقيقي.
4. Frontend يستخدم JavaScript/JSX؛ لا توجد حاليًا TypeScript typecheck أو ESLint scripts/dependencies في `frontend/package.json`. يلزم تقييم فحص ساكن تدريجي قبل إضافة gate أو اعتماديات.
5. P7 غير جاهزة: لا يوجد نشر إنتاجي مثبت. ما زالت بوابات الاستضافة المجانية بلا بطاقة، HTTPS، SMTP حي، كفاية موارد ClamAV، الأسرار خارج Git، ووجهة نسخ احتياطي خارجية مع اختبار استعادة فعلية.

- لا تغيير API/DB/migrations أو اعتماديات runtime في PRs #129/#133/#136/#137/#140/#141. الميزانية صفر؛ لا موارد مدفوعة أو دفع إلكتروني، ولا تجاوز لحماية GitHub.


## نقطة تحقق مؤكدة — 2026-11-07 — PRs #145 و#147 و#146

> هذه اللقطة تخص **Lumen Learning Platform فقط**، المستودع HVA09/lumen-learning-platform. لا تُستخدم أي حالة أو SHA أو فحص من مستودع ai-chat-app.

### مرجع المستودع والفرع

- المستودع: https://github.com/HVA09/lumen-learning-platform
- الفرع الأساسي: main عند 38eb15b01719d544d7d04a0c93d4fa4d4e3d6a6d، وهو commit دمج PR #143 الخاص باختبار تعافي WebSocket بعد عودة الشبكة.
- قراءة GitHub تعرض main.protected=true. أعاد استعلام Rulesets قائمة فارغة، لكن واجهة GitHub رفضت قراءة تفاصيل Branch Protection (403)؛ لذلك لا نسجل أسماء Required Status Checks أو سياسة الموافقات من دون دليل.
- وقت التحقق: 2026-11-07. جميع PRs الثلاثة مفتوحة، غير مدمجة، وغير Draft، وGitHub يعرضها mergeable=true في وقت اللقطة.

### حالة الطلبات

| PR | النطاق | الرأس الحالي | الفحوص |
|---|---|---|---|
| [#145](https://github.com/HVA09/lumen-learning-platform/pull/145) | اختبارات lazy routes وfeature callbacks في frontend/src/App.test.jsx فقط | 6ad9b54c72dbb1ee21600dc911b0922a7d4682bd | [Lumen CI #42295018064](https://github.com/HVA09/lumen-learning-platform/actions/runs/42295018064) — 4/4 ناجحة |
| [#147](https://github.com/HVA09/lumen-learning-platform/pull/147) | Nginx WebSocket proxy، include مشترك لمسارات HTTP/HTTPS، وBrowser E2E يمر عبر Nginx | b543573616d122eb4c374f92e4d44384697a8c8a | [Lumen CI #42383718753](https://github.com/HVA09/lumen-learning-platform/actions/runs/42383718753) — 4/4 ناجحة |
| [#146](https://github.com/HVA09/lumen-learning-platform/pull/146) | عزل مختبر Python باستخدام iframe opaque-origin وPyodide Blob Worker واختبارات عزل | d51953b6acf9bfa80d84448857e6569106f76bda | [Lumen CI #42399378562](https://github.com/HVA09/lumen-learning-platform/actions/runs/42399378562) — 4/4 ناجحة |

#### تفاصيل التبعيات وحجم التغيير

- قاعدة الطلبات الثلاثة جميعها هي SHA نفسه: 38eb15b01719d544d7d04a0c93d4fa4d4e3d6a6d. المقارنة مع main وقت التحقق: #145 متقدم 1 commit، #147 متقدم 13 commits، #146 متقدم 20 commits، ولا يوجد أي منها خلف main في هذه اللقطة.
- #145 يغيّر ملف اختبار واحدًا فقط (+132/-10). لا يغيّر Runtime أو API أو DB أو Dependencies أو Secrets أو إعدادات النشر.
- #147 يغيّر 7 ملفات (+176/-58). يشمل إعدادات Nginx وDocker Compose وCI وBrowser E2E والوثائق. اختبار CI يتحقق من nginx -t ومن مرور REST/WebSocket عبر حاوية Nginx. **لا يفعّل هذا PR TLS في الإنتاج**؛ كتل HTTPS والتحويل تبقى معطلة إلى حين وجود دومين حقيقي وشهادة صالحة، ويظل اختبار WSS على مضيف حقيقي مطلوبًا بعد التهيئة.
- #146 يغيّر 7 ملفات (+876/-106). توثيق docs/PYTHON_LAB_SECURITY.md يوضح أن العزل هو Browser-origin isolation، وليس OS-level sandbox. لا توجد حصة ذاكرة صلبة لـ Web Worker؛ لا يُسمح بوصفه كحاوية آمنة لتشغيل كود عدائي غير محدود. يجب إبقاء هذا القيد ظاهرًا في أي إعلان إطلاق.
- عالج الرأس الحالي لـ #146 ملاحظة التغطية السابقة: اختبار Playwright يشغّل fetch من Pyodide Blob Worker الحقيقي ويتطلب حدث securitypolicyviolation بــ effectiveDirective=connect-src وdisposition=enforce وأصل URI المحظور المطابق للـ API. لا يكفي رفض Promise أو CORS/شبكة وحده. ملاحظة PR تسجل Backend **480 passed, 21 warnings** في CI الأخير.

### نتائج CI الدقيقة

تتكون بوابة Lumen CI في كل تشغيل من أربع وظائف، وقد اكتملت جميعها بنجاح على SHA المذكور لكل PR:
1. Frontend tests and production build.
2. Backend tests.
3. Browser E2E (registration and browser session).
4. Full Git history secret scan.

نجاح CI لا يعني أن PR مدمج، ولا يثبت نشرًا حيًا، ولا يستبدل مراجعة تغييرات المصدر. التعليقات الآلية على #145 و#147 و#146 تسجل أن Codex review لم يكتمل بسبب بلوغ حد استخدام مراجعات Codex؛ لا نصنف ذلك على أنه مراجعة ناجحة أو finding تقني مؤكد. يجب إبقاء حالة المراجعة منفصلة عن حالة CI.

### التسلسل الآمن المقترح

1. دمج #145 أولاً بعد موافقة المالك والتحقق الفوري من SHA وحالة CI.
2. بعده إعادة قراءة main ودمج #147 إذا ظل diff قابلًا للدمج وفحوص الرأس ما زالت خضراء؛ ثم التحقق من CI على main بعد الدمج.
3. تحديث/إعادة تأسيس فرع #146 على أحدث main بعد الدمجين، وحل أي تعارضات بمراجعة محددة وعدم استبدال الملفات كاملة.
4. تشغيل وظائف Lumen CI الأربع مجددًا على رأس #146 الجديد، والتأكد خصوصًا من Browser E2E الذي يختبر Pyodide Worker وCSP الفعلية.
5. دمج #146 فقط بعد نجاح الوظائف الأربع ومراجعة حدود الأمان، ثم التحقق من تشغيل CI على main بعد الدمج.
6. لا تعتبر #147 تفعيلًا لـ HTTPS، ولا تعتبر #146 عزلًا على مستوى نظام التشغيل أو حدًا لذاكرة العامل.

### ما لم يحدث في هذه اللقطة

- لم يُدمج أي من #145 أو #147 أو #146.
- لم تتغير ملفات التطبيق أو قاعدة البيانات أو أسرار الإنتاج أو إعدادات الاستضافة.
- لم يُنفّذ Deploy أو تغيير TLS أو إعادة فهرسة أو أي إجراء مدفوع.
- التوثيق وحده لا يمثل موافقة على دمج أي PR.

### المتبقي خارج هذه المجموعة

بوابات P7 التشغيلية لا تزال منفصلة عن هذه PRs: استضافة مجانية مناسبة بلا بطاقة، HTTPS فعلي، SMTP حي، التحقق من موارد ClamAV على مضيف الاستضافة، أسرار الإنتاج خارج Git، ونسخة احتياطية خارجية مشفرة مع اختبار استعادة فعلي. لا نسجل اكتمال P7 أو وجود نشر إنتاجي من نجاح CI وحده.
