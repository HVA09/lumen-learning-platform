# الحالة التنفيذية لمشروع Lumen Learning Platform

آخر تحقق: **2026-11-04**.

> هذه الوثيقة هي نقطة الاستئناف المعتمدة. تحقّق دائمًا من أحدث commit وGitHub Actions قبل أي تغيير؛ لا تعتمد على تواريخ المحادثات أو حالة قديمة.

## الملخص التنفيذي

- المستودع: [HVA09/lumen-learning-platform](https://github.com/HVA09/lumen-learning-platform) — عام.
- الفرع الأساسي: `main`.
- آخر commit متحقق على `main`: `ee149a40b144883b0fea34232ae730574d5e5ed7` بعد دمج PR #46.
- PR #4 و#29–#46 مدمجة. شملت الدفعة الأخيرة PR #39 (إصلاح Compose للنسخ الخارجي)، و#40 (Gamification scoring)، و#41 (WebSocket lifecycle)، و#42 (خريطة معمارية الواجهة)، و#43 (Session Hook)، و#44 (Notifications state hook)، و#45 (خط أساس الجودة)، و#46 (نقل الإشعارات إلى Feature مستقلة).
- PR #30 دُمج في 2026-11-03. بقي المسار القديم `app.services.quiz_logic` كواجهة توافق.
- CI #526 نجح على رأس PR #30، وCI #532 على PR #31، وCI #534 على PR #32؛ جميع وظائف Backend وFrontend/build وFull Git history secret scan نجحت.
- CI #537 نجح على main قبل PR #34: Backend **404 passed** وFrontend **51 passed**.
- CI #539 نجح على main بعد PR #34: Backend **405 passed** وFrontend **51 passed**.
- CI #541 نجح على main بعد PR #35: Backend **407 passed** وFrontend **51 passed**.
- CI #543 نجح على main بعد PR #36: Backend **407 passed** وFrontend **51 passed**.
- CI #545 على `de79d3e4` نجاح تاريخي على خط أساس أقدم. بعد PR #46، نجحت جميع وظائف CI على رأس PR نفسه `959ab53f21f51d76eec02ddab1542333384fec32` في التشغيل [#41744744642](https://github.com/HVA09/lumen-learning-platform/actions/runs/41744744642). بدأ CI بعد الدمج على `main` عند `ee149a40b144883b0fea34232ae730574d5e5ed7` في التشغيل [#41745646366](https://github.com/HVA09/lumen-learning-platform/actions/runs/41745646366)، وكان جاريًا عند آخر تحقق؛ لا نسجل نجاحه قبل اكتماله.
- لا يوجد نشر إنتاجي مثبت.

## حالة المراحل

| المرحلة | الحالة | الدليل / المخرج |
|---|---|---|
| P0 — تثبيت خط الأساس | مكتمل | PR #4 و#29 مدمجان؛ CI #525 نجح على خط الأساس السابق لـ P1 |
| P1 — استخراج منطق Assessments | مكتمل | PR #30 مدمج، وCI #526 و#527 ناجحان |
| P2 — خريطة حدود المجالات والاعتماديات | مكتمل توثيقيًا | توثيق الاعتماديات والملكية الأولية في `ARCHITECTURE_PLAN.md` وADR-017؛ لا نقل إضافي قبل قرار مستقل |
| P3 — تجربة Backend ثانية صغيرة | مكتمل | PR #32 مدمج؛ CI #534 على PR وCI #535 على main نجحا |
| P4 — فصل حدود خدمات Backend | منفذ جزئيًا | PR #34/#35 (Learning Progress)، و#37 (Review/SRS)، و#40 (Gamification scoring) مدمجة؛ تبقى فرص فصل أخرى حسب تحليل الاعتماديات |
| P5 — تنظيم Frontend | P5.1–P5.4 مكتملة | PR #41 WebSocket، و#43 Session، و#44 Notifications state، و#46 نقل الإشعارات إلى `features/notifications` مدمجة؛ PR #42 وثّق الخريطة والخطة |
| P6 — الجودة والأداء والمراقبة | خط الأساس موثق؛ التنفيذ لم يبدأ | ESLint/Ruff وtypecheck وcoverage وBrowser E2E وميزانية الأداء ليست بوابات CI بعد؛ أولوية P6.1 تشغيل lint كتقرير فقط |
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
- [PR #42](https://github.com/HVA09/lumen-learning-platform/pull/42) دُمج في `main` بالـ commit `aaeeb38e0b16c0ee2d2cea3664a6a3b6b00e1eac`؛ [CI بعد الدمج #41744012439](https://github.com/HVA09/lumen-learning-platform/actions/runs/41744012439) كان جاريًا عند آخر تحقق.
- [CI #41742892283](https://github.com/HVA09/lumen-learning-platform/actions/runs/41742892283): تشغيل `main` على commit `b63574af` بعد PR #39 (تاريخي).
- [CI #41744744642](https://github.com/HVA09/lumen-learning-platform/actions/runs/41744744642): نجح بالكامل على رأس PR #46؛ Backend وFrontend/build وdependency audit وGitleaks وفحوصات Compose وmigrations وbackup/restore كلها ناجحة.
- [PR #46](https://github.com/HVA09/lumen-learning-platform/pull/46) دُمج بالـ commit `ee149a40b144883b0fea34232ae730574d5e5ed7`؛ [CI بعد الدمج #41745646366](https://github.com/HVA09/lumen-learning-platform/actions/runs/41745646366) كان جاريًا عند آخر تحقق.

## ما تم إنجازه

- استيراد الواجهة والخلفية إلى المستودع وتوحيد خط الأساس عبر PR #4.
- تحسينات المصادقة والجلسات وCSRF وTOTP وتشفير أسرار TOTP وقواعد إنشاء المسؤول الأول.
- حماية مسارات رفع الملفات والتحقق من النوع والحجم وفحص البرمجيات الخبيثة باستخدام ClamAV مع حصص تخزين لكل مستخدم.
- إضافة idempotency لمعالجة Webhooks.
- إعداد اختبارات PostgreSQL للترحيلات والحفاظ على البيانات والنسخ الاحتياطي والاستعادة.
- إضافة مسار اختياري للنسخ الاحتياطي الخارجي المشفر باستخدام Restic؛ لم يتم إعداد مزود خارجي حقيقي بعد.
- تشغيل CI للواجهة والخلفية وفحص الأسرار في تاريخ Git الكامل.
- اعتماد Modular Monolith كاتجاه معماري، وتنفيذ وحدات Assessments وLearning Progress وReview/SRS وGamification النقية مع واجهات توافق عند الحاجة.
- استخراج دورة WebSocket إلى `useNotificationsSocket`، وإدارة الجلسة إلى `useSession`، وحالة الإشعارات والقراءات إلى `useNotifications` عبر PRs #41/#43/#44؛ كلها مدمجة.
- إصلاح escaping لمتغير فترة النسخ الخارجي في Docker Compose مع assertion للـ rendered command عبر PR #39.

## الوضع المعماري الحالي

- Backend: FastAPI + PostgreSQL. ما زالت معظم المكونات منظمة أفقيًا في `auth/` و`routers/` و`models/` و`schemas/` و`services/`.
- Assessments: منطق التصحيح والتحقق والاختيار والإتقان في `app/modules/assessments/domain/quiz_logic.py`، ومنطق تحليل الأسئلة النقي في `app/modules/assessments/domain/question_analytics.py`. المساران القديمان في `app/services/` واجهتا توافق.
- Learning Progress: قاعدتا `compute_streak` و`topic_progress` في `app/modules/learning_progress/domain/` بعد PR #34 و#35، مع واجهات توافق. يبقى `study_activity.py` مسؤولًا عن التخزين، و`build_learning_path` جامعًا لبيانات Catalog وProgress داخل service.
- Review/SRS: انتقال SM-2+ النقي وEnum `CardState` في `app/modules/review/domain/sm2.py` بعد PR #37؛ يبقى `ReviewCard` في ORM والخدمة محولًا متوافقًا، وmigration 0010 دون تغيير.
- Frontend: React 19 + Vite. المكونات ما زالت أساسًا في `src/components`، وعملاء API حسب المجال في `src/lib`. Hooks الحالية تشمل `useSession` و`useNotifications` و`useNotificationsSocket` و`useDirection` في `src/hooks`.
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

1. P0–P3 مكتملة. P4 نُفذت جزئيًا عبر PR #34/#35/#37/#40. P5.1–P5.4 مدمجة عبر PR #41/#43/#44/#46.
2. P4 أضافت `app/modules/gamification/domain/scoring.py` عبر PR #40؛ تبقى الاستعلامات المجمعة server-side في `app/services/achievements.py`.
3. لا تنقل `achievements.py` ككتلة واحدة؛ شروط الإنجازات تستعلم عبر مجالات عدة، ويجب تحديد عقود قراءة مستقلة قبل فصلها. لا تنقل كل الواجهة دفعة واحدة.
4. P5.1–P5.4 مكتملة ومدمجة؛ نُقلت الإشعارات واختباراتها وطبقة API إلى `frontend/src/features/notifications/` مع الإبقاء على عميل HTTP المشترك وعقود API وCSRF وسلوك RTL/LTR. الخطوة الهندسية التالية P6.1: تشغيل ESLint وRuff كتقرير أولي دون فرض بوابات جديدة قبل تحليل النتائج.
