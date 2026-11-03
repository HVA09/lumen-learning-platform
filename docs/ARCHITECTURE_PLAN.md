# الخطة المعمارية الحالية والمراحل التنفيذية لمنصة Lumen

آخر تحديث: **2026-11-03**  
مرجع `main` بعد PR #35: `0c725181a8cd1bfd4062cc828f4cc3ee58a5aec3`  
PR #30 و#32 و#33 و#34 و#35 مدمجة؛ CI #541 نجح على main. Backend: 407 passed؛ Frontend: 51 passed؛ build وGitleaks وCompose وmigrations وbackup/restore وRestic نجحت.

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
- `src/components/` للمكونات و`src/lib/` لعملاء API حسب المجال.
- يوجد عميل HTTP مركزي يعتمد Cookies من نوع HttpOnly وCSRF.
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
| Review / SRS | بطاقات المستخدم وجدولة المراجعة | ReviewCard, spaced_repetition |
| Classes | الفصول والتسجيل وعضوية الطلاب والدعوات | ClassSection, ClassEnrollment, invite services |
| Assignments | إنشاء الواجبات والتسليم والتقييم | Assignment, AssignmentSubmission |
| Files | المرفقات والتحقق والفحص والتخزين | FileAttachment, files router, malware_scanner |
| Gamification | الإنجازات والنقاط ولوحة المتصدرين | UserAchievement, achievements (تستهلك مؤشرات النشاط من Learning Progress) |
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

- `spaced_repetition.py` يحتوي قواعد SM-2+ لكنه يستقبل نموذج ORM `ReviewCard` ويعدّله مباشرةً in-place.
- قبل فصله، ينبغي تعريف حالة مجال مستقلة أو دالة نقية تستقبل القيم وتعيد الحالة الجديدة، ثم تترك Application Service يحفظ التغييرات.
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
| P4 | فصل حدود خدمات Learning/Progress/SRS/Gamification | قيد التنفيذ جزئيًا — PR #34 و#35 فصلا قواعد Learning Progress النقية؛ التالي تصميم فصل SM-2 عن ORM وعقود القراءة العابرة للمجالات |
| P5 | تنظيم Frontend تدريجيًا | بعد خريطة features/shared وعقود API واختبارات RTL/LTR |
| P6 | lint/typecheck واختبارات متصفح وتحسين الأداء والمراقبة | تحديد الأدوات وخط الأساس قبل فرضها |
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

- آخر main بعد PR #35: `0c725181a8cd1bfd4062cc828f4cc3ee58a5aec3`.
- CI #541 نجح بالكامل: 407 Backend tests، و51 Frontend tests عبر 11 ملفًا، production build، Gitleaks full-history، Compose، migrations، PostgreSQL backup/restore، وRestic smoke test.
- P0–P3 مكتملة. P4 قيد التنفيذ جزئيًا؛ نُقلت قاعدتا streak وtopic progress، مع إبقاء التخزين وتجميع المنهج في طبقة الخدمة.
- لا يوجد نشر إنتاجي مثبت.
- لا يوجد نشر إنتاجي مثبت.
