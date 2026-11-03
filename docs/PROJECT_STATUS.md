# الحالة التنفيذية لمشروع Lumen Learning Platform

آخر تحقق: **2026-11-03**.

> هذه الوثيقة هي نقطة الاستئناف المعتمدة. تحقّق دائمًا من أحدث commit وGitHub Actions قبل أي تغيير؛ لا تعتمد على تواريخ المحادثات أو حالة قديمة.

## الملخص التنفيذي

- المستودع: [HVA09/lumen-learning-platform](https://github.com/HVA09/lumen-learning-platform) — عام.
- الفرع الأساسي: `main`.
- آخر commit متحقق على `main` بعد PR #35: `0c725181a8cd1bfd4062cc828f4cc3ee58a5aec3`.
- PR #4 مستورد خط الأساس ومُدمج، وPR #29 أصلح بصمات Gitleaks بعد squash merge، وPR #30 نقل منطق الاختبارات إلى مجال Assessments، وPR #31 حدّث التوثيق وCI لمسارات docs، وPR #32 نقل تحليل الأسئلة إلى Assessments، وPR #33 وثّق اكتمال P3، وPR #34 فصل قاعدة streak إلى Learning Progress، وPR #35 فصل قواعد حالة الموضوع والتوصية؛ جميعها مدمجة.
- PR #30 دُمج في 2026-11-03. بقي المسار القديم `app.services.quiz_logic` كواجهة توافق.
- CI #526 نجح على رأس PR #30، وCI #532 على PR #31، وCI #534 على PR #32؛ جميع وظائف Backend وFrontend/build وFull Git history secret scan نجحت.
- CI #537 نجح على main قبل PR #34: Backend **404 passed** وFrontend **51 passed**.
- CI #539 نجح على main بعد PR #34: Backend **405 passed** وFrontend **51 passed**.
- CI #541 على commit `main` الحالي `0c725181` **نجح بالكامل**: Backend **407 passed, 0 failed, 20 warnings**؛ Frontend **51 passed عبر 11 ملف اختبار**؛ production build وGitleaks full-history وCompose وmigrations وPostgreSQL backup/restore وRestic smoke test كلها ناجحة.
- لا يوجد نشر إنتاجي مثبت.

## حالة المراحل

| المرحلة | الحالة | الدليل / المخرج |
|---|---|---|
| P0 — تثبيت خط الأساس | مكتمل | PR #4 و#29 مدمجان؛ CI #525 نجح على خط الأساس السابق لـ P1 |
| P1 — استخراج منطق Assessments | مكتمل | PR #30 مدمج، وCI #526 و#527 ناجحان |
| P2 — خريطة حدود المجالات والاعتماديات | مكتمل توثيقيًا | توثيق الاعتماديات والملكية الأولية في `ARCHITECTURE_PLAN.md` وADR-017؛ لا نقل إضافي قبل قرار مستقل |
| P3 — تجربة Backend ثانية صغيرة | مكتمل | PR #32 مدمج؛ CI #534 على PR وCI #535 على main نجحا |
| P4 — فصل حدود خدمات Backend | قيد التنفيذ جزئيًا | PR #34 و#35 أكملا فصل قاعدتي streak وtopic progress؛ ما زال فصل انتقال SM-2 عن ORM وتحليل عقود الخدمات العابرة للمجالات مطلوبًا |
| P5 — تنظيم Frontend | لم يبدأ | إعداد خريطة features/shared وعقود API واختبارات RTL/LTR |
| P6 — الجودة والأداء والمراقبة | جزئي / مخطط | CI موجود؛ lint/typecheck واختبارات متصفح وقياس أداء ومراقبة تحتاج baseline |
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
- [CI #541](https://github.com/HVA09/lumen-learning-platform/actions/runs/41677706751): **نجح بالكامل على main** commit `0c725181a8cd1bfd4062cc828f4cc3ee58a5aec3`؛ 407 Backend و51 Frontend.

## ما تم إنجازه

- استيراد الواجهة والخلفية إلى المستودع وتوحيد خط الأساس عبر PR #4.
- تحسينات المصادقة والجلسات وCSRF وTOTP وتشفير أسرار TOTP وقواعد إنشاء المسؤول الأول.
- حماية مسارات رفع الملفات والتحقق من النوع والحجم وفحص البرمجيات الخبيثة باستخدام ClamAV مع حصص تخزين لكل مستخدم.
- إضافة idempotency لمعالجة Webhooks.
- إعداد اختبارات PostgreSQL للترحيلات والحفاظ على البيانات والنسخ الاحتياطي والاستعادة.
- إضافة مسار اختياري للنسخ الاحتياطي الخارجي المشفر باستخدام Restic؛ لم يتم إعداد مزود خارجي حقيقي بعد.
- تشغيل CI للواجهة والخلفية وفحص الأسرار في تاريخ Git الكامل.
- اعتماد Modular Monolith كاتجاه معماري، ثم تنفيذ وحدتي Assessments النقيتين `quiz_logic.py` و`question_analytics.py` مع واجهات توافق للمسارات القديمة عبر PR #30 و#32.

## الوضع المعماري الحالي

- Backend: FastAPI + PostgreSQL. ما زالت معظم المكونات منظمة أفقيًا في `auth/` و`routers/` و`models/` و`schemas/` و`services/`.
- Assessments: منطق التصحيح والتحقق والاختيار والإتقان في `app/modules/assessments/domain/quiz_logic.py`، ومنطق تحليل الأسئلة النقي في `app/modules/assessments/domain/question_analytics.py`. المساران القديمان في `app/services/` واجهتا توافق.
- Learning Progress: قاعدتا `compute_streak` و`topic_progress` في `app/modules/learning_progress/domain/` بعد PR #34 و#35، مع واجهات توافق. يبقى `study_activity.py` مسؤولًا عن التخزين، و`build_learning_path` جامعًا لبيانات Catalog وProgress داخل service.
- Frontend: React 19 + Vite. عملاء API مقسمون حسب المجال في `src/lib`، والمكونات في `src/components`.
- يجب المحافظة على جلسات HttpOnly وCSRF، وعقود API الحالية، والعربية/الإنجليزية، وRTL/LTR، وتجربة الهاتف.
- سجل النماذج الصريح في `app/models/__init__.py` ضروري لاكتشاف Alembic؛ لا تنقل النماذج قبل خطة تسجيل واختبارات ترحيل.

## نتيجة مراجعة الاعتماديات الأولية لـ P2

- `question_analytics.py`: دوال نقية لتحليل الأسئلة نُقلت إلى `modules/assessments/domain` عبر PR #32؛ بقيت استعلامات SQL وتجميع استجابة API داخل `routers/content.py`.
- `learning_path.py`: `build_learning_path` منسق يجمع بيانات Catalog وProgress ويشكّل مسار الطالب؛ قواعد حالة الموضوع والتوصية منفصلة في Learning Progress domain عبر PR #35.
- `study_activity.py`: خدمة مرتبطة بقاعدة البيانات لقراءة وكتابة `StudyDay`؛ تستورد قاعدة حساب السلسلة من `modules/learning_progress/domain/streak_logic.py` عبر PR #34.
- `learning_path.py`: يبقى منسقًا/جامعًا لبيانات الموضوعات والمواد والدروس والأسئلة؛ قواعد حالة الموضوع واختيار التوصية انتقلت إلى domain عبر PR #35.
- `spaced_repetition.py`: الخوارزمية مرتبطة حاليًا مباشرة بنموذج ORM `ReviewCard` وتعدله in-place؛ لا تُعامل كمنطق نقي قبل فصل حساب الحالة عن التخزين.
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

1. P0–P3 مكتملة ومتحقق منها، وP4 بدأت بتنفيذ حدّي Learning Progress: PR #34 و#35 مدمجان؛ أحدث خط أساس ناجح هو CI #541 على `0c725181`.
2. فصل `streak_logic` و`topic_progress` مكتمل. يبقى تحليل وفصل انتقال حالة SM-2 عن ORM مع الحفاظ على Enum والمخطط الحالي.
3. لا تنقل `achievements.py` ككتلة واحدة؛ هي خدمة استعلامات عابرة لمجالات متعددة وتحتاج عقود قراءة واضحة.
4. بعد حسم حدود SRS وGamification، انتقل إلى خريطة Frontend features/shared وعقود API.
