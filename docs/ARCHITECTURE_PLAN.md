# الخطة المعمارية الحالية والمراحل التنفيذية لمنصة Lumen

آخر تحديث: **2026-11-04**  
آخر تغيير برمجي على `main` هو PR #67 عند `2453b9124fc4eaa617aa5bb5493ebc0cf1400c9a`. آخر commit على `main` وقت هذا التحديث هو `11d6695913bc0b6587225c95489c4abffd7ff9a0` (توثيق PR #67)، وCI بعد الدمج [#41903896915](https://github.com/HVA09/lumen-learning-platform/actions/runs/41903896915) نجح بالكامل: Backend 423 passed/20 warnings، Frontend 80 passed/16 files، Ruff 0 diagnostics، production build وGitleaks وفحوص migrations وbackup/restore ناجحة.
PR #39–#46 و#48 و#49 و#51–#59 و#62 و#64–#67 مدمجة (باستثناء PR #55 المغلق دون دمج). PR #59/#62/#64 حسّنت code splitting، وPR #65 أضاف Vite preload recovery، وPR #67 قلّص precache من 35 ملفًا/1328.16 KiB إلى 8 ملفات/378.63 KiB.

> الغرض هو تنظيم النظام تدريجيًا دون إعادة كتابة، أو تغيير سلوك الميزات، أو تعريض بيانات المستخدمين والترحيلات للخطر.

## 1. القرار المعماري

اعتماد **Modular Monolith**:

- تطبيق Backend واحد وقاعدة PostgreSQL واحدة.
- وحدات داخلية مرتبة بحسب مجالات العمل.
- طبقات داخل كل مجال تفصل قواعد المجال عن HTTP والتخزين والتكاملات.
- لا Microservices ولا قواعد بيانات منفصلة في المرحلة الحالية.
- لا تنقل ملفات لمجرد تغيير أسماء المجلدات؛ كل نقل يجب أن يثبت حدود ملكية واضحة واختبارات قابلة للتراجع.

الاتجاه المقصود للاعتماديات:

`Router → Application Service / Use Case → Domain Rules`

وتتصل الخدمات/المجالات عبر عقود واضحة، لا عبر استيراد Router من Router.

## 2. الوضع الفعلي

### Backend

البنية الأساسية ما زالت أفقية في معظمها:

- `auth/`: المصادقة والجلسات والعامل الثاني.
- `routers/`: واجهات HTTP حسب المسار.
- `models/`: نماذج ORM.
- `schemas/`: عقود Pydantic.
- `services/`: منطق المجال والتنسيق والاستعلامات، وما زالت بعض مسؤولياتها مختلطة.

أول وحدة مجال جديدة موجودة الآن:

- `app/modules/assessments/domain/quiz_logic.py`: قواعد تصحيح وتطبيع الإجابات والتحقق واختيار الأسئلة وحساب الإتقان.
- `app/services/quiz_logic.py`: واجهة توافق تعيد تصدير الواجهة العامة نفسها للمستهلكين الذين لم ينتقلوا بعد.
- `app/modules/assessments/domain/question_analytics.py`: دوال نقية لتحليل أداء السؤال وتصنيفه وترتيب الأسئلة التي تحتاج مراجعة؛ مدمجة عبر PR #32.
- `app/services/question_analytics.py`: واجهة توافق تعيد تصدير الرموز العامة نفسها؛ يستورد Router والاختبار الأساسي المجال مباشرةً.
- أُضيف اختبار توافق يتحقق من تطابق هوية كل رمز عام بين المسارين القديم والجديد.
- `app/modules/learning_progress/domain/streak_logic.py`: PR #34 ينقل قاعدة حساب أيام الدراسة المتتالية النقية إلى Learning Progress.
- `app/services/streak_logic.py`: واجهة توافق؛ تستورد `study_activity.py` القاعدة من المسار الجديد مباشرةً.
- `app/modules/learning_progress/domain/topic_progress.py`: قواعد تحديد حالة الموضوع والموضوع الموصى به؛ مدمجة عبر PR #35.
- `app/services/learning_path.py`: يبقى مسؤولًا عن تجميع البيانات الواردة من Catalog وProgress وبناء بنية مسار التعلم؛ يعيد تصدير قواعد الموضوع القديمة للتوافق.

### Frontend

- React 19 + Vite.
- `src/components/` للمكونات العامة و`src/lib/api.js` لعميل HTTP المشترك المعتمد على HttpOnly Cookies وCSRF.
- `src/features/notifications/` أول Feature مكتملة النقل: `api/notificationsApi.js`، و`components/NotificationBell.jsx` واختبارها، و`hooks/useNotifications.js` و`hooks/useNotificationsSocket.js` واختباراتهما، مع `index.js` كنقطة تصدير عامة.
- `App.jsx` و`AppHeader.jsx` يستوردان من مدخل Feature العام، بينما يبقى عميل HTTP/CSRF المشترك في `src/lib/api.js`.
- يجب المحافظة على العربية والإنجليزية وRTL/LTR وتصميم الهاتف أثناء أي إعادة تنظيم.
- لا تبدأ عملية نقل شاملة إلى `features/shared` قبل خريطة ملكية المكونات والبيانات وعقود API.

### التسجيل والترحيلات

- `app/models/__init__.py` يستورد النماذج صراحةً لتسجيلها في `Base.metadata` واكتشاف Alembic.
- أي نقل لنموذج يجب أن يحافظ على التسجيل والعلاقات ومفاتيح الاستيراد واختبارات upgrade/downgrade.
- PR #30 لم يغيّر قاعدة البيانات أو migrations أو عقود API.

## 3. حدود المجالات الأولية

| المجال | المسؤولية التي ينبغي أن يملكها | الأصول الحالية ذات الصلة |
|---|---|---|
| Identity & Access | المستخدمون والأدوار والمصادقة والجلسات و2FA | `auth/`, User, AuthSession |
| Learning Catalog | المواد والمواضيع والدروس والمحتوى التعليمي | Subject, Topic, Lesson, TopicCard |
| Assessments | بنك الأسئلة والمحاولات والتصحيح وتحليل عناصر الاختبار | Question, QuizAttempt, QuestionResult, quiz_logic, question_analytics |
| Learning Progress | الإتقان وتقدم الدروس والنشاط الدراسي وقواعد streak وحالة الموضوع والتوصية | TopicMastery, LessonProgress, StudyDay, study_activity, streak_logic, topic_progress |
| Review / SRS | بطاقات المستخدم وجدولة المراجعة | ReviewCard, review/domain/sm2, spaced_repetition adapter |
| Classes | الفصول والتسجيل وعضوية الطلاب والدعوات | ClassSection, ClassEnrollment, invite services |
| Assignments | إنشاء الواجبات والتسليم والتقييم | Assignment, AssignmentSubmission |
| Files | المرفقات والتحقق والفحص والتخزين | FileAttachment, files router, malware_scanner |
| Gamification | الإنجازات والنقاط ولوحة المتصدرين | UserAchievement, achievements, scoring rules (تستهلك مؤشرات النشاط من Learning Progress) |
| Notifications | الإشعارات وقنوات التسليم | Notification, notifications |
| Billing | الخطط والاشتراكات وأحداث الدفع | Plan, Subscription, ProcessedWebhookEvent |
| LTI Integration | تسجيل LMS وOIDC وربط الهوية وAGS | LTIPlatform, LTI routers/services |
| Administration & Audit | الإدارة والأحداث التدقيقية | admin router, AuditLog |

هذه حدود مقترحة؛ ليست كلها مطبقة كحزم مستقلة بعد.

## 4. خريطة الاعتماديات التي ظهرت في فحص P2

### Assessments

- `quiz_logic.py` أصبح في المجال الجديد.
- `question_analytics.py` دوال نقية بلا ORM أو FastAPI؛ نُقلت إلى `modules/assessments/domain` عبر PR #32 مع واجهة توافق واختبارات.
- `routers/content.py` ما زال يحتوي إدارة الدروس واستعلامات SQL لتجميع نتائج الأسئلة وبناء استجابة API؛ لذلك يخلط بين مسؤولية Learning Catalog ومسؤولية Assessments على مستوى الـ Router. فصل المسارات/التنسيق يتم لاحقًا بعقود مستقلة، وليس ضمن هذا النقل.

### Learning Catalog وLearning Progress

- `learning_path.py` يحتوي `build_learning_path`، وهو منسق نقي يستقبل بيانات مجمعة مسبقًا عن Catalog وProgress ويشكّل المخرجات؛ يبقى في service لأنه يجمع مسؤوليات عرض متعددة ولا يملك قاعدة مجال واحدة.
- `compute_topic_status` و`pick_recommended_topic` قاعدتان نقيتان لملكية Progress، موجودتان الآن في `modules/learning_progress/domain/topic_progress.py` بعد دمج PR #35 واختبارات التوافق وثبات ترتيب المنهج.
- `routers/curriculum.py` يجمع بيانات ORM من Subject وTopic وLesson وTopicMastery، ثم يستدعي منسق المسار ويسجل نشاط الدراسة ويفحص الإنجازات.

### Study Activity وGamification

- `streak_logic.py` قاعدة نقية لحساب أيام الدراسة المتتالية؛ نُقلت في PR #34 إلى `modules/learning_progress/domain` مع واجهة توافق للمسار القديم.
- `topic_progress.py` يملك قواعد حالة الموضوع واختيار التوصية بعد PR #35؛ لا يملك تجميع مخرجات المنهج.
- `study_activity.py` خدمة تخزين وقراءة مرتبطة بـ SQLAlchemy ونموذج StudyDay، وتستورد القاعدة من المجال دون امتلاك منطق حساب السلسلة.
- `achievements.py` يجمع استعلامات من QuizAttempt وTopicMastery وAssignmentSubmission وLessonProgress وReviewCard وUserAchievement، ويعتمد على Study Activity.
- هذه خدمة عابرة للمجالات؛ لا تُنقل بكاملها إلى Gamification دون تصميم عقود/استعلامات قراءة واضحة.

### Review / SRS

- `app/modules/review/domain/sm2.py`: PR #37 ينقل CardState وReviewState وانتقال SM-2+ النقي إلى مجال Review بلا SQLAlchemy.
- `app/services/spaced_repetition.py`: يبقى محولًا بين القيمة المجالّية ونموذج ORM؛ ويحافظ على `review_card(card, grade, now) -> card` كواجهة متوافقة تعيد نفس الكائن.
- Enum `CardState` في المجال يحتفظ باسم الصنف وأسماء الأعضاء والقيم والترتيب نفسها؛ SQLAlchemy ما زال ينشئ enum `cardstate` مطابقًا للمخطط الحالي.
- `app/models/review_card.py` يعيد تصدير CardState من المجال؛ schema وmodel registry يظلان على مساراتهما الحالية.
- migration `0010_review_cards.py` لم تتغير؛ يحافظ Enum على الاسم `cardstate` والقيم والترتيب `new, learning, review, relearning`.
- CI #544 على PR #37 وCI #545 على main نجحا؛ 417 اختبار Backend و51 اختبار Frontend، دون migration أو API changes.
- `routers/srs.py` ينسق ملكية البطاقة، الاستيراد/التصدير، نشاط الدراسة، وفحص الإنجازات؛ لا ينقل ككتلة واحدة.

### Classes وAssignments

- `routers/assignments.py` يعتمد على ClassSection وClassEnrollment للتحقق من ظهور الواجب وعضوية الطالب.
- الفصل في الملكية لا يعني منع التحقق من العضوية؛ يجب أن يصبح عبر خدمة/استعلام واضح بدل تكرار قواعد الصلاحية.
- يجب أن تظل قواعد المعلم والطالب والصف واضحة في اختبارات API.

### قواعد لا بد من حمايتها

1. لا يوجد Router يستورد Router آخر.
2. لا تجعل خدمة مجال تعدل Models مجال آخر مباشرةً دون عقد واضح.
3. لا تكرر قواعد الأعمال داخل Routers.
4. لا تكسر الاستيرادات العامة قبل طبقة توافق وفترة انتقالية واختبارات.
5. لا تغيّر API أو Schema أو DB ضمن مهمة نقل تنظيمية بحتة.
6. لا تنقل النماذج قبل ضمان تسجيلها في SQLAlchemy/Alembic.

## 5. خطة التنفيذ المحدثة

| المرحلة | العمل | الحالة |
|---|---|---|
| P0 | تثبيت خط الأساس الأمني والاختباري | مكتمل — PR #4 و#29 مدمجان؛ CI #525 ناجح |
| P1 | استخراج منطق Assessments الخالص quiz_logic | مكتمل — PR #30 مدمج وCI #526 و#527 ناجحان |
| P2 | خريطة ملكية المجالات والاعتماديات | مكتمل توثيقيًا — التبعيات والمخاطر والمرشح التالي موثقة |
| P3 | استخراج وحدة نقية ثانية صغيرة | مكتمل — PR #32 مدمج؛ CI #534 على PR وCI #535 على main ناجحان |
| P4 | فصل حدود خدمات Learning/Progress/SRS/Gamification | منفذ جزئيًا: Progress عبر PR #34/#35، وReview/SRS عبر PR #37، وGamification scoring عبر PR #40؛ تبقى الحدود الأخرى وفق الأولوية والتحليل |
| P5 | تنظيم Frontend تدريجيًا | P5.1–P5.4 مكتملة ومدمجة؛ PR #46 نقل الإشعارات إلى `features/notifications` واختُبر قبل الدمج وبعده |
| P6 | الجودة والأداء والمراقبة | Ruff 0 diagnostics report-only؛ ESLint لم يبدأ بسبب قيد npm registry؛ code splitting في #59/#62/#64، وpreload recovery في #65، وسياسة PWA في #67 خفّضت precache 71.5% إلى 8 entries/378.63 KiB. CI ما بعد الدمج #41903896915 ناجح بالكامل؛ ما زالت قياسات RUM وBrowser E2E وTypecheck وCoverage لاحقة، وتوجد تنبيهات اعتماديات تطوير منخفضة/متوسطة موثقة في ADR-033 |
| P7 | الإطلاق | بعد إغلاق متطلبات الاستضافة والأمن والتشغيل |

## 6. بوابات القبول لكل تغيير

- تشغيل الاختبارات المركزة أولًا ثم Backend suite كاملة.
- تشغيل Frontend tests وproduction build وفحص الاعتماديات.
- نجاح فحص Gitleaks على نطاق PR والتاريخ الكامل وكل refs.
- عند وجود migrations: اختبار upgrade وdowngrade والحفاظ على البيانات على PostgreSQL.
- مراجعة diff للتأكد من أن التغيير التنظيمي لم يغير السلوك أو عقود API.
- توثيق SHA وCI وروابط PR في `PROJECT_STATUS.md`.
- فصل نجاح CI عن اختبار المضيف الحقيقي أو LMS sandbox أو موافقة GitHub.

## 7. ما لن نفعله

- لا إعادة كتابة كاملة ولا Microservices دون سبب مثبت.
- لا نقل كل Models أو Routers في commit واحد.
- لا تعطيل ClamAV أو فحوصات الأمن لتناسب خطة استضافة صغيرة.
- لا دمج سلسلة LTI القديمة مباشرة؛ تعاد تهيئتها على main الحالي وتختبر migrations والتكامل.
- لا نشر أو إنشاء موارد مدفوعة دون موافقة المستخدم.
- لا تجاوز حماية GitHub أو تزوير مراجعة.

## 8. نقطة الاستئناف

- آخر تغيير برمجي على `main`: `2453b9124fc4eaa617aa5bb5493ebc0cf1400c9a` بعد PR #67؛ CI بعد الدمج والتوثيق [#41903896915](https://github.com/HVA09/lumen-learning-platform/actions/runs/41903896915) نجح بالكامل على `11d6695913bc0b6587225c95489c4abffd7ff9a0`.
- P4: فواصل Progress وReview وGamification scoring منفذة عبر PR #34/#35/#37/#40.
- P5.1–P5.4 مدمجة: WebSocket (#41)، خريطة Frontend (#42)، session (#43)، notification state (#44)، ثم نقل Notifications إلى `features/notifications` (#46). CI #41745646366 نجح بعد الدمج.
- P6.1: Ruff 0.17.3 مفعّل للخلفية كتقرير فقط والنتيجة الحالية 0 diagnostic(s). PR #52 و#53 أتما معالجة Ruff، وPR #55 تجربة ESLint جزئية أُغلقت دون دمج، وPR #56 أزال ثلاثة findings مؤكدة، وPR #57/#58 حدّثا السجلات. لا يوجد ESLint معتمد في `main`؛ بيئة التنفيذ الحالية لا تصل إلى npm registry ولا تحتوي cache للحزم، لذلك لا يُنشأ lockfile يدويًا.
- P6.5: PR #59/#62/#64/#65/#67 مدمجة: code splitting للوحدات التعليمية، واسترداد Vite preload، وتقليل precache في #67 من 35 entries/1328.16 KiB إلى 8/378.63 KiB (نحو 71.5%). في PR CI #41876997024: Backend 423/20 warnings، Ruff 0، Frontend 80/16 files، build وGitleaks ناجحة. CI بعد الدمج [#41903896915](https://github.com/HVA09/lumen-learning-platform/actions/runs/41903896915) نجح على main. لا يوجد قياس أداء ميداني أو Browser E2E حتى الآن.
- سلسلة LTI #16–#23 تحتاج إعادة تأسيس وخطة migration/integration مستقلة؛ لا تدمج مباشرة.
- لا يوجد نشر إنتاجي مثبت.
