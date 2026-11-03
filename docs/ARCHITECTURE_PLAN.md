# الخطة المعمارية الحالية والمراحل التنفيذية لمنصة Lumen

آخر تحديث: **2026-11-03**  
مرجع `main`: `57d85d7c776afb3b65f8579b6c12361fd8c03ea6`  
PR #30 دُمج؛ CI #526 نجح على رأسه قبل الدمج، وCI #527 نجح على commit الدمج. Backend: 403 passed؛ Frontend: 51 passed؛ build وGitleaks وmigrations وbackups نجحت.

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
- `app/modules/assessments/domain/question_analytics.py`: دوال نقية لتحليل أداء السؤال وتصنيفه وترتيب الأسئلة التي تحتاج مراجعة؛ قيد النقل عبر PR #32.
- `app/services/question_analytics.py`: واجهة توافق أثناء الانتقال؛ استيراد Router والاختبارات الجديدة يستهدف المجال مباشرةً.
- تم تحويل Routers وSchemas واختبارات المجال إلى المسار الجديد، مع اختبار تطابق الواجهة القديمة.

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
| Learning Progress | الإتقان وتقدم الدروس والنشاط الدراسي | TopicMastery, LessonProgress, StudyDay, study_activity |
| Review / SRS | بطاقات المستخدم وجدولة المراجعة | ReviewCard, spaced_repetition |
| Classes | الفصول والتسجيل وعضوية الطلاب والدعوات | ClassSection, ClassEnrollment, invite services |
| Assignments | إنشاء الواجبات والتسليم والتقييم | Assignment, AssignmentSubmission |
| Files | المرفقات والتحقق والفحص والتخزين | FileAttachment, files router, malware_scanner |
| Gamification | الإنجازات والنقاط ولوحة المتصدرين | UserAchievement, achievements, streak logic |
| Notifications | الإشعارات وقنوات التسليم | Notification, notifications |
| Billing | الخطط والاشتراكات وأحداث الدفع | Plan, Subscription, ProcessedWebhookEvent |
| LTI Integration | تسجيل LMS وOIDC وربط الهوية وAGS | LTIPlatform, LTI routers/services |
| Administration & Audit | الإدارة والأحداث التدقيقية | admin router, AuditLog |

هذه حدود مقترحة؛ ليست كلها مطبقة كحزم مستقلة بعد.

## 4. خريطة الاعتماديات التي ظهرت في فحص P2

### Assessments

- `quiz_logic.py` أصبح في المجال الجديد.
- `question_analytics.py` دوال نقية بلا ORM أو FastAPI؛ يستوردها `routers/content.py` وتختبر في `test_question_analytics.py`.
- `routers/content.py` يحتوي أيضًا إدارة الدروس؛ لذلك يخلط حاليًا بين مسؤولية Learning Catalog ومسؤولية Assessments.
- التوصية التالية: تقييم نقل `question_analytics.py` إلى `modules/assessments/domain` مع واجهة توافق، بعد إكمال خريطة P2.

### Learning Catalog وLearning Progress

- `learning_path.py` دوال نقية تستقبل بيانات موحدة عن المواد والإتقان والدروس والأسئلة وتبني المسار الموصى به.
- `routers/curriculum.py` يجمع بيانات ORM من Subject وTopic وLesson وTopicMastery، ثم يستدعي منطق المسار ويسجل نشاط الدراسة ويفحص الإنجازات.
- يلزم حسم هل ملكية بناء المسار ضمن Learning Progress أم Application Use Case يجمع Catalog وProgress. لا تحسم ذلك بنقل ملف قبل توثيق قواعد الملكية.

### Study Activity وGamification

- `streak_logic.py` دالة نقية لحساب أيام الدراسة المتتالية.
- `study_activity.py` خدمة تخزين وقراءة مرتبطة بـ SQLAlchemy ونموذج StudyDay.
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
| P3 | استخراج وحدة نقية ثانية صغيرة | قيد التنفيذ عبر PR #32: question_analytics مع واجهة توافق |
| P4 | فصل خدمات Learning/Progress/SRS/Gamification | بعد عقود ملكية واختبارات تكامل لكل مجال |
| P5 | تنظيم Frontend تدريجيًا | بعد خريطة features/shared وعقود API |
| P6 | lint/typecheck واختبارات متصفح وتحسين الأداء والمراقبة | تحديد الأدوات وbaseline قبل فرضها |
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

- آخر main بعد PR #31: `57d85d7c776afb3b65f8579b6c12361fd8c03ea6`.
- CI #526 ناجح على رأس PR #30.
- CI #527 على main بعد الدمج نجح بالكامل: 403 Backend tests، و51 Frontend tests عبر 11 ملفًا، production build، Gitleaks full-history، Compose، migrations، PostgreSQL backup/restore، وRestic smoke test.
- P1 منجز بالدمج والتحقق. P2 مكتمل توثيقيًا. P3 قيد التنفيذ عبر PR #32 لاستخراج `question_analytics.py`.
- لا يوجد نشر إنتاجي مثبت.
