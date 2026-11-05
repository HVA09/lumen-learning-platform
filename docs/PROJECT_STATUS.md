# الحالة التنفيذية لمشروع Lumen Learning Platform

آخر تحقق: **2026-11-05**.

> هذه الوثيقة هي نقطة الاستئناف المعتمدة. تحقّق دائمًا من أحدث commit وGitHub Actions قبل أي تغيير؛ لا تعتمد على تواريخ المحادثات أو حالة قديمة.

## الملخص التنفيذي

- المستودع: [HVA09/lumen-learning-platform](https://github.com/HVA09/lumen-learning-platform) — عام.
- الفرع الأساسي: `main`.
- آخر تغيير برمجي مدمج على `main`: PR #77 عند commit `451572c1253351e0b4406ed21480b659b2862406` (Squash Merge). وسّع Playwright Browser E2E لاختبار واجهة الطالب والمعلم والمسؤول، منع الطالب من مسارات المحتوى والإدارة، قدرة المعلم على إدارة المحتوى وإنشاء فصله، عزل الفصول بين معلمين مختلفين (403 عند الوصول لفصل الآخر)، ووصول المسؤول المصرح به. حسابات الأدوار مؤقتة وتُرقّى حصريًا داخل PostgreSQL المحلي المؤقت `lumen_e2e` مع فحص host واسم القاعدة وتطابق إعدادات التطبيق؛ لا توجد نقطة ترقية أدوار جديدة في التطبيق. التغيير البرمجي محصور في `frontend/e2e/smoke_test.py` ولا يغيّر منطق التطبيق أو API أو schema أو migrations أو الاعتماديات. CI على PR [#41940578786](https://github.com/HVA09/lumen-learning-platform/actions/runs/41940578786) وبعد الدمج على `main` [#41941142454](https://github.com/HVA09/lumen-learning-platform/actions/runs/41941142454) نجحا بجميع الوظائف الأربع.
- PR #4 و#29–#46 و#48 و#49 و#51–#54 و#56–#59 و#62 و#64–#77 مدمجة، بما فيها PR #68 و#69 و#76 التوثيقيتين وPR #70/#73/#75/#77 لتوسيع Browser E2E. PR #55 مغلق دون دمج. PR #59/#62/#64 خفّضت التحميل الأولي، و#65 أضاف Vite preload recovery، و#67 خفّض precache إلى 8 entries/378.63 KiB.
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
| P6 — الجودة والأداء والمراقبة | P6.0 وP6.1 الخلفية مكتملان؛ P6.5 تحسين الأداء مدمج؛ P6.6 تغطي التسجيل والجلسة (#70)، وإكمال الدرس واستعادة التقدم (#73)، وتسليم Quiz وحفظ سجل المحاولات (#75)، ومصفوفة صلاحيات الطالب/المعلم/المسؤول وعزل ملكية الفصول (#77). CI على PR #77 (#41940578786) وبعد الدمج على `main` (#41941142454) نجحا 4/4. المتبقي: دورة إنشاء/تعديل/نشر/حذف المحتوى (PR #78 قيد الاختبار)، درجات Quiz الصحيحة وعتبة النجاح، الملفات وفحص ClamAV، الإشعارات/WebSocket، RTL/LTR، وانقطاع/عودة الشبكة؛ قياسات RUM وCore Web Vitals الميدانية غير مكتملة. |
| P7 — الإطلاق | غير جاهز | بوابات الاستضافة والتشغيل أدناه لم تُغلق |

## آخر نقاط التحقق

- [CI #41925605855](https://github.com/HVA09/lumen-learning-platform/actions/runs/41925605855): نجح على رأس PR #75 `87e3778b581e4a04e275024defa080b194e0ba62` بالوظائف الأربع؛ Browser E2E أثبت بدء Quiz تدريبي وتسليم محاولة بلا إجابات، عدم كشف مفاتيح الإجابة في استجابة البدء، إرجاع تصحيح وتغذية راجعة من الخادم، وظهور المحاولة ودرجتها في سجل الخادم بعد reload.
- [CI #41938791393](https://github.com/HVA09/lumen-learning-platform/actions/runs/41938791393): نجح بعد دمج PR #75 على `main` عند commit `1c94e4f73695b675d8929daf25b35c8d718aac5d`؛ الوظائف الأربع نجحت. Backend **423 passed, 20 warnings**؛ Frontend **80 passed عبر 16 ملفًا**؛ Ruff **0 diagnostics**؛ production audit **0 vulnerabilities**؛ full dependency audit **2 Low و4 Moderate، وصفر High/Critical**؛ Browser E2E وGitleaks full-history نجحا.
- [CI #41940578786](https://github.com/HVA09/lumen-learning-platform/actions/runs/41940578786): نجح على رأس PR #77 `b71abeca28cdfd8da8e2f43c6c3f3010ae636b60` بالوظائف الأربع؛ Browser E2E أثبت إخفاء أزرار الإدارة والمحتوى عن الطالب، صلاحيات المعلم وإدارة المحتوى، حصر كل معلم على فصله ورفض الوصول إلى فصل المعلم الآخر، وصلاحيات المسؤول.
- [CI #41941142454](https://github.com/HVA09/lumen-learning-platform/actions/runs/41941142454): نجح بعد دمج PR #77 على `main` عند `451572c1253351e0b4406ed21480b659b2862406`؛ Backend وFrontend/build وBrowser E2E وGitleaks full-history كلها نجحت.

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

1. PR #70 و#73 و#75 و#77 مدمجة. CI على PR #77 (#41940578786) وبعد الدمج على `main` (#41941142454) نجحا 4/4. اختبار المتصفح يغطي التسجيل والجلسة الآمنة، حفظ تقدم الدرس، تسليم Quiz وحفظ المحاولة، ثم أدوار الطالب والمعلم والمسؤول وعزل الفصول بين المعلمين.
2. PR #78 مفتوح لاختبار دورة نشر الدرس عبر Content Manager: إنشاء مسودة غير منشورة، إثبات غيابها عن قائمة الطالب، نشرها من واجهة المعلم، ثم إثبات ظهورها في قائمة الطالب. لا يُعد مكتملًا قبل نجاح وظائف CI الأربع.
3. بعد دورة الدرس، أضف اختبارًا مركزًا لإنشاء سؤال وتعديله وتعطيله/تفعيله من الواجهة، والتحقق من عدم كشف الإجابة الصحيحة للطالب، ثم اختبار تصحيح Quiz بإجابات صحيحة وخاطئة والتحقق من عتبة النجاح. أضف الحذف مع تأكيد نافذة المتصفح إذا لزم.
4. رفع الملفات والتنزيل والحذف وعزل ملفات المستخدمين مرحلة منفصلة. لا تختبر نجاح الرفع قبل إثبات توفر ClamAV في بيئة الاختبار؛ يجب أن يفشل الرفع بشكل مغلق إذا تعذر الفحص.
5. أضف الإشعارات/WebSocket، RTL/LTR، وانقطاع الاتصال وعودته على تدفقات المتعلم الأساسية. لا تدّعِ أن PWA تجعل API/WebSocket تعمل دون اتصال.
6. P4 منفذة جزئيًا عبر PR #34/#35/#37/#40؛ لا تنقل `achievements.py` ككتلة واحدة قبل تصميم عقود قراءة واضحة عبر المجالات.
7. Ruff 0.17.3 ما زال report-only بنتيجة **0 diagnostic(s)**. أحدث تدقيق كامل مسجل في CI السابق #41938791393: 2 Low و4 Moderate وصفر High/Critical، بينما production audit سجل صفرًا؛ لا تستخدم `npm audit fix --force` دون تحديث واختبار متوافق.
8. تبقى سلسلة LTI/AGS #16–#23 بحاجة إلى إعادة تأسيس وتحليل تعارضات وترحيلات ثم اختبار Sandbox؛ لا تدمجها مباشرة.
9. لا يوجد نشر إنتاجي مثبت. ما زالت بوابات P7 تشمل مضيفًا مجانيًا لا يتطلب بطاقة/فاتورة، HTTPS فعليًا، SMTP، تقييم ClamAV على موارد المضيف، أسرار إنتاج خارج Git، ووجهة Restic خارجية مع اختبار استعادة حقيقي.