# الحالة التنفيذية لمشروع Lumen Learning Platform

آخر تحقق: **2026-11-04**.

> هذه الوثيقة هي نقطة الاستئناف المعتمدة. تحقّق دائمًا من أحدث commit وGitHub Actions قبل أي تغيير؛ لا تعتمد على تواريخ المحادثات أو حالة قديمة.

## الملخص التنفيذي

- المستودع: [HVA09/lumen-learning-platform](https://github.com/HVA09/lumen-learning-platform) — عام.
- الفرع الأساسي: `main`.
- آخر commit متحقق على `main`: `09d2a706236b4f9be55f3d8c66d461fee34f70c1` بعد دمج PR #64.
- PR #4 و#29–#46 و#48 و#49 و#51–#54 و#56–#59 و#62 و#64 مدمجة. PR #51 حدّث سجلات الحالة بعد Ruff، وPR #52 جعل إعادة التصدير في واجهات التوافق صريحة، وPR #53 خفّض نتائج Ruff من 62 إلى صفر، وPR #54 و#57 و#58 حدّثت التوثيق الدائم، وPR #56 أزال ثلاثة findings مؤكدة في الواجهة، وPR #59 خفّض الحزمة الأولية بتحميل لوحة الدرس عند الطلب، وPR #62 أجّل Markdown/KaTeX، وPR #64 أجّل الاختبارات والمختبر والمحاكاة حتى يطلبها المتعلم.
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
| P6 — الجودة والأداء والمراقبة | P6.0 وRuff baseline مكتملان؛ P6.5 تحسن تدريجي مدمج عبر PR #59/#62/#64 | Ruff 0 diagnostics report-only. entry الأولي 362.89 kB (116.82 kB gzip)، وTopicPanel انخفض إلى 6.76 kB (2.47 gzip)، وQuizPanel وLabPanel والمحاكاة تُحمّل عند الطلب. MathTextRenderer مؤجل حتى ظهور MathText. القياس من build وليس RUM؛ E2E وقياس الأداء الميداني لم يكتملَا. |
| P7 — الإطلاق | غير جاهز | بوابات الاستضافة والتشغيل أدناه لم تُغلق |

## آخر نقاط التحقق

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

1. P0–P3 مكتملة. P4 منفذة جزئيًا عبر PR #34/#35/#37/#40؛ لا تنقل `achievements.py` ككتلة واحدة قبل تصميم عقود القراءة العابرة للمجالات.
2. P5.1–P5.4 مكتملة ومدمجة: WebSocket (#41)، خريطة Frontend (#42)، Session (#43)، notification state (#44)، ونقل Notifications إلى `features/notifications` (#46). تحقّق CI #41745646366 بنجاح على `main` بعد الدمج.
3. أُضيف Ruff 0.17.3 عبر PR #49 بوضع report-only على `app`, `tests`, `scripts`, و`migrations`. عولجت إعادة التصدير المقصودة في PR #52، ثم الاستيرادات والتعيينات وأسماء المتغيرات في PR #53؛ التقرير الحالي **0 diagnostic(s)**. يبقى Ruff report-only. ESLint للواجهة لم يُثبّت أو يُشغّل بعد؛ يجب أولًا توليد `package-lock.json` باستخدام npm والتحقق بـ `npm ci` قبل تسجيل أي baseline.
4. تبقى سلسلة LTI/AGS #16–#23 بحاجة إلى إعادة تأسيس وتحليل تعارضات وترحيلات ثم اختبار Sandbox؛ لا تدمجها مباشرة.
5. لا يوجد نشر إنتاجي مثبت. اختبار Restic الحالي يستخدم مستودعًا مؤقتًا في CI وليس وجهة تخزين خارجية حقيقية.
6. آخر تحديث برمجي: PR #64 مدمج في `main` عند `09d2a706236b4f9be55f3d8c66d461fee34f70c1`؛ PR CI #41857581931 وmain CI #41858290575 نجحا بالكامل. Backend 423 passed و20 warnings، Frontend 74 passed عبر 14 ملفًا، Ruff 0 diagnostics. entry 362.89 kB (116.82 gzip)، TopicPanel 6.76 kB (2.47 gzip)، QuizPanel 4.88 kB، LabPanel 1.80 kB، والمحاكاة ملفات مستقلة؛ MathTextRenderer 442.53 kB مؤجل عند الحاجة. لم نثبت بعد قياس RUM أو زمن التحميل على جهاز/شبكة فعلية. ESLint وTypecheck وCoverage وBrowser E2E ما زالت ضمن P6.
