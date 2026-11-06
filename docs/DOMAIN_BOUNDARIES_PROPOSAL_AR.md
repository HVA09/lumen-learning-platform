# مقترح حدود المجالات والوحدات لمنصة Lumen

> **الحالة:** تصميم أولي للمراجعة، وليس تصريحاً بنقل الملفات.  
> **تاريخ الإعداد:** 2026-10-30  
> **مرجع الكود:** `fix/security-production-hardening` عند `f3e7b899db42090bb00f1cc3048808f210dc746a`.

## 1. الهدف

تحديد من يملك البيانات وقواعد الأعمال قبل تحويل البنية الأفقية الحالية (`routers/`, `models/`, `schemas/`, `services/`) إلى وحدات مجال واضحة. لا يكفي جمع الملفات ذات الاسم المتشابه؛ يجب أن يعكس التقسيم مسؤوليات المنتج واتجاه اعتمادياته.

التقسيم المقترح Modular Monolith. كل وحدة مستقلة منطقياً داخل التطبيق الواحد، وتستخدم قاعدة البيانات الحالية ما لم تظهر حاجة مثبتة للفصل.

## 2. الوحدات المقترحة وملكية المسؤوليات

| الوحدة | المسؤولية الأساسية | الأصول الحالية المرشحة للملكية |
|---|---|---|
| Identity & Access | حسابات المستخدمين، المصادقة، الجلسات، الأدوار و2FA | `auth/`, `routers/users.py`, `models/user.py`, `schemas/auth.py`, `schemas/user.py`, `dependencies.py`, `password_policy.py` |
| Learning Catalog | المواد والمواضيع والدروس ومتطلبات فتح المواضيع ومحتواها | `models/subject.py`, `topic.py`, `lesson.py`, `topic_card.py`, `routers/curriculum.py`, `routers/content.py`, `schemas/curriculum.py`, `schemas/content.py`, `services/learning_path.py`, `content/` |
| Assessments | بنك الأسئلة ومحاولات الاختبار والتصحيح ونتائج الأسئلة وتحليلاتها | `models/question.py`, `question_result.py`, `quiz_attempt.py`, `routers/quiz.py`, `schemas/quiz.py`, `services/quiz_logic.py`, `services/question_analytics.py` |
| Learning Progress | تقدم المتعلم، سجل النشاط، الإتقان وتجميع مؤشرات التقدم | `models/topic_mastery.py`, `models/study_day.py`, `routers/reports.py`, `services/study_activity.py`, `services/reports.py` |
| Review / Spaced Repetition | بطاقات المراجعة وجدولة التكرار المتباعد | `models/review_card.py`, `routers/srs.py`, `schemas/srs.py`, `services/spaced_repetition.py` |
| Gamification | الإنجازات، النقاط، الأيام المتتالية ولوحة المتصدرين | `models/user_achievement.py`, `routers/gamification.py`, `schemas/gamification.py`, `services/achievements.py`, `services/streak_logic.py` |
| Classes | الفصول والتسجيل ورموز الدعوة وعلاقات المعلم والطلاب | `models/class_section.py`, `routers/classes.py`, `schemas/class_section.py`, `services/invite_codes.py` |
| Assignments | الواجبات والتسليمات والتقييم وملاحظات المعلم | `models/assignment.py`, `routers/assignments.py`, `schemas/assignment.py` |
| Files | ملكية الملفات، التحقق منها، التخزين والتنزيل والحذف | `models/file_attachment.py`, `routers/files.py`, `schemas/file.py` |
| Billing | الخطط والاشتراكات ودورة حياة الدفع والأحداث الواردة من المزود | `models/plan.py`, `models/subscription.py`, `routers/billing.py`, `schemas/billing.py`, `services/payment_providers/` |
| Notifications | حفظ الإشعارات وإرسالها وتحديثها وقنوات التسليم | `models/notification.py`, `routers/notifications.py`, `schemas/notification.py`, `notifications.py` |
| LTI Integration | تكامل LTI 1.3، منصات LMS وروابط المستخدم وحالات المصادقة | `models/lti.py`, `routers/lti.py`, `schemas/lti.py`, `services/lti_service.py` |
| Administration & Audit | عمليات الإدارة والتدقيق ومراجعة العمليات الحساسة | `routers/admin.py`, `schemas/admin.py`, `models/audit_log.py`, `audit.py` |

**ملاحظات ملكية مهمة:**

- `User` كيان هوية مركزي، لكن لا يعني ذلك السماح لكل وحدة بتغيير بيانات الحساب مباشرة. التعديلات يجب أن تمر عبر واجهة Identity واضحة.
- `TopicMastery` يقع عند الحد بين Assessments وLearning Progress. المقترح أن تكون ملكية سجل الإتقان في Learning Progress، وأن ترسل Assessments نتيجة تقييم مكتملة عبر خدمة تطبيقية/عقد داخلي لتحديث الإتقان.
- `StudyDay` أقرب إلى سجل تقدم/نشاط، وليس إلى خوارزمية المراجعة؛ لذا يظل ضمن Learning Progress ما لم يكشف تدقيق الاستعلامات خلاف ذلك.
- Gamification يستهلك أحداث النشاط والتقدم ويمنح الإنجازات، ولا ينبغي أن يعيد تنفيذ قواعد التصحيح أو حساب الإتقان.
- Reports طبقة استعلام وتجميع تقرأ بيانات عدة مجالات. لا تصبح مالكاً لبياناتها الأصلية.
- Classes وAssignments مجالان منفصلان، لكن Assignment قد يعتمد على تحقق Classes من التسجيل في فصل. لا ينبغي لراوتر الواجبات أن يستورد راوتر الفصول.
- LTI وPayment تكاملات خارجية ذات حدود أمنية؛ توضع في طبقات التكامل المناسبة ولا تخلط داخل منطق المجال العام.
- Audit وLogging وDatabase وCache وQueue وEmail قدرات بنية تحتية مشتركة، وليست مكاناً عاماً لأي منطق أعمال.

## 3. الهيكل المقترح داخل Backend

~~~text
backend/app/
├── core/                         # config, security primitives, exceptions
├── api/
│   └── v1/                        # تجميع endpoints الحالية دون تغيير مساراتها
├── modules/
│   ├── identity/
│   ├── learning/
│   ├── assessments/
│   ├── progress/
│   ├── review/
│   ├── gamification/
│   ├── classes/
│   ├── assignments/
│   ├── files/
│   ├── billing/
│   ├── notifications/
│   ├── administration/
│   └── integrations/
│       └── lti/
├── infrastructure/
│   ├── database/
│   ├── cache/
│   ├── queue/
│   ├── storage/
│   ├── email/
│   └── observability/
└── main.py
~~~

هذا رسم منطقي، وليس دعوة إلى إنشاء جميع هذه المجلدات فارغة. ننشئ الوحدة عند نقل وظيفة حقيقية إليها، ونختار داخلها أبسط تقسيم يلزمها. يمكن أن تكون بعض الوحدات صغيرة ولا تحتاج كل طبقة.

## 4. الهيكل المقترح داخل Frontend

| Feature | ملفات الواجهة الحالية المرشحة |
|---|---|
| auth | `AuthForm`, `AccountSettings`, `VerifyEmailPage`, `ResetPasswordPage`, `authApi`, أجزاء واجهة المستخدم |
| learning | `LearningPath`, `TopicPanel`, `LabPanel`, `ContentManager`, `curriculumApi`, `contentApi`, المحاكيات |
| assessments | `QuizPanel`, `quizApi` |
| review | `FlashcardReview`, `srsApi` |
| progress | `ProgressPanel`, `reportsApi` |
| gamification | `LeaderboardPanel`, `gamificationApi` |
| classes | `ClassesPanel`, `classesApi` |
| assignments | `AssignmentsPanel`, `assignmentsApi` |
| files | `FilesPanel`, `filesApi` |
| billing | `BillingPanel`, `BillingSuccessPage`, `BillingCancelPage`, `billingApi` |
| notifications | `NotificationBell`, `notificationsApi` |
| administration | `AdminDashboard`, `adminApi` |
| integrations/lti | `LTICallbackPage` |
| app/shared | `AppHeader`, `ErrorBoundary`, `Toast`, `LanguageToggle`, `ThemeToggle`, `MathText` بعد التأكد من أنها عامة فعلاً، وعميل HTTP المشترك |

تُحفظ ملفات الاختبارات بجانب الوحدة/الميزة التي تختبرها، ولا تنقل إلى مجلد عام بعيد عنها.

## 5. قواعد اتجاه الاعتماديات

### Backend

الاتجاه المسموح المقترح:

~~~text
HTTP Router
    ↓
Application Service / Use Case
    ↓
Domain Rules + Data Access
    ↓
Database Models / External Adapters
~~~

قواعد إلزامية:
1. لا يستورد Router من Router آخر.
2. لا تستدعي الوحدة خدمة داخلية عميقة في وحدة أخرى. تستخدم عقداً واضحاً أو خدمة تطبيقية معلنة.
3. لا تكرر قواعد الصلاحيات أو الملكية في أكثر من مكان؛ تُعرّف في مجالها وتُستدعى عبر واجهة موثوقة.
4. لا تستخدم الوحدة جداول مجال آخر لتعديلها مباشرة. القراءة العابرة للمجالات يجب أن تكون مقصودة وواضحة، والكتابة تمر عبر مالك البيانات.
5. لا نجعل `core/` أو `shared/` مستودعاً عشوائياً للكود؛ نضع فيهما القدرات العامة فقط.
6. تظل قاعدة البيانات واحدة حالياً، ولا نضيف خدمات منفصلة أو قواعد بيانات متعددة بلا مبرر.
7. تُحافظ مسارات API الحالية على التوافق أثناء النقل؛ لا تغيير للمسارات أو العقود إلا في إصدار/قرار منفصل.

### Frontend

~~~text
app (routes, providers, layouts)
      ↓
features
      ↓
shared
~~~

قواعد إلزامية:
1. `shared` لا يستورد من `features`.
2. ميزة لا تستورد تفاصيل داخلية من ميزة أخرى؛ التواصل يكون عبر props أو واجهات معلنة أو حالة تطبيق مشتركة عند الحاجة.
3. لا تضع مكوناً في `shared` لمجرد أنه قابل للاستيراد؛ يجب أن يكون عاماً فعلاً.
4. API clients الخاصة بمجال تنتقل معه، أما إعداد Axios/interceptors فيبقى ضمن shared infrastructure.
5. لا نغيّر شكل الواجهة أو السلوك ضمن عملية نقل الملفات إلا عندما توجد مهمة UX مستقلة ومختبرة.

## 6. عقود التكامل بين المجالات

توجد عدة تدفقات تتطلب حدوداً مقصودة:

| التدفق | صاحب القرار | ما يستلمه المجال الآخر |
|---|---|---|
| تسليم اختبار ← تحديث الإتقان | Assessments يصدر نتيجة مصححة؛ Progress يملك سجل الإتقان | attempt result/score/pass outcome |
| نشاط تعلم ← إنجاز أو سلسلة أيام | Learning/Progress يسجل النشاط؛ Gamification يقيّم قواعد المكافآت | حدث نشاط موثق |
| واجب مرتبط بفصل | Classes يجيب عن التسجيل والملكية؛ Assignments يقرر إظهار/تسليم الواجب | نتيجة تحقق من التسجيل/الدور |
| عملية دفع ناجحة ← تعديل اشتراك | Billing يملك حالة الاشتراك ويعالج webhook موثّقاً | حدث دفع موثوق ومميز بمعرّف idempotency |
| رفع ملف ← إشعار المستخدم | Files يملك نتيجة التخزين؛ Notifications يملك التسليم | حدث ملف مرفوع/محذوف |
| LTI تسجيل مستخدم ← Identity | LTI يتحقق من بيانات المنصة؛ Identity يملك حساب المستخدم والربط | طلب ربط/إنشاء مستخدم عبر واجهة معلنة |

هذه العقود منطق تصميم مستهدف. يجب مراجعة تدفقات التنفيذ الحالية قبل اعتماد أسماء الأنواع أو نقل الاستدعاءات.

## 7. ترتيب تنفيذ الحدود

1. حسم اعتماد نسخة التطبيق في PR #4. لا يبدأ نقل ملفات على أساس `main` الحالي الناقص.
2. إنشاء خريطة اعتماديات تفصيلية للوحدة التجريبية التي سنختارها.
3. تحديد مالك نماذج البيانات المشتركة والعقود بين الوحدات.
4. اختيار وحدة منخفضة المخاطر وذات اختبارات كافية لتجربة النمط.
5. نقل عمودي صغير مع إبقاء API compatibility، وتحديث Alembic model registration عند الحاجة.
6. تشغيل اختبارات الوحدة والتكامل والبناء، ومراجعة diff قبل متابعة أي وحدة أخرى.

**لا نحدد الوحدة التجريبية بشكل نهائي قبل مراجعة استيراداتها واستدعاءاتها الفعلية واختباراتها.** يمنع ذلك اختيار مجال يبدو بسيطاً من أسماء الملفات بينما يعتمد في الواقع على مجالات كثيرة.

## 8. ما لم يُقرر بعد

هذه القرارات مؤجلة إلى حين مراجعة الكود والتدفقات:
- هل تكون `TopicMastery` جزءاً من Progress أم من Learning.
- هل تبقى تقارير الإدارة في وحدة Reports مستقلة أم تكون Query Services ضمن Administration.
- هل تكون `notifications.py` خدمة تطبيقية ضمن Notifications أم Adapter ضمن Infrastructure.
- ما الخدمات التي تحتاج Repository فعلياً، وما الخدمات التي تكون ORM queries مباشرة داخل use case.
- أي وحدة أفضل كـ pilot بعد مقارنة عدد الاعتماديات ومخاطر الانحدار وتغطية الاختبار.

**القرار:** حدود الوحدات أعلاه نقطة بداية للمراجعة وليست خريطة نقل نهائية. لا يتغير الكود بناءً عليها قبل إغلاق الأسئلة المفتوحة وتحديد خطة اختبار وتراجع لكل وحدة.
