# الخطة المعمارية الحالية والمراحل التنفيذية لمنصة Lumen

آخر تحديث: **2026-11-06**  
آخر تغيير برمجي مدمج على `main`: PR #97 عند `fc25ba75987403a85154e55fc70f329d38ee6371`، ويغطي استعادة جلسة المتعلم بعد انقطاع الشبكة وعودتها دون إعادة تحميل. CI بعد الدمج #42115046453 نجح 4/4.
PR #95 مدمج عند `80be944a39ffd683daa4ee24cabe48a3bd9067c7` لمعالجة session bootstrap بعد عودة الاتصال، وPR #97 مدمج عند `fc25ba75987403a85154e55fc70f329d38ee6371` لاختبار Browser E2E. CI بعد PR #95 #42113922307 وبعد PR #97 #42115046453 نجحا 4/4.
PR #39–#46 و#48 و#49 و#51–#59 و#62 و#64–#84 و#87–#89 و#91 و#95 و#97 مدمجة (باستثناء PR #55 و#86 المغلقين دون دمج). PR #100 مفتوح على فرع العمل لقياس تغطية Backend واختبارات المهام الخلفية؛ لا يدخل ضمن main قبل الدمج.

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
| P6 | الجودة والأداء والمراقبة | Ruff 0 diagnostics report-only؛ ESLint لم يُعتمد بعد؛ code splitting في #59/#62/#64، وpreload recovery في #65، وPWA precache في #67 خُفّض 71.5%. اختبارات P6.6 عبر #70–#97 تغطي التسجيل والجلسة والتقدم والنشر والاختبارات والصلاحيات وفحص الملفات والإشعارات وRTL/LTR واستعادة الجلسة. PR #100: Backend coverage **89% / 431 passed** (CI #42223767240 4/4). PR #102: Frontend coverage **31.80% statements** (91 passed/17 files، CI #42207211737 4/4). PR #101: SMTP tests، Backend **437 passed** و`email_service.py` **92%** (CI #42126717163 4/4)، stacked على #100. PR #103: أربعة API adapter test suites؛ Frontend **112 passed/21 files** والبناء وGitleaks PR+all-refs نجحت في #42224962672، وBackend/Browser E2E قيد التنفيذ. جميع هذه PRs مفتوحة وغير مدمجة. المتبقي: إعادة baseline التغطية بعد دمج التغييرات، LTI/OIDC/Files/ClamAV tests، RUM/Core Web Vitals، Typecheck وقياسات الهاتف والاتصال البطيء. |
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

- آخر تغيير برمجي مدمج على `main`: PR #97 عند `fc25ba75987403a85154e55fc70f329d38ee6371`. CI بعد الدمج #42115046453 نجح 4/4؛ PR #95 السابق مدمج أيضًا وCI بعده #42113922307 نجح 4/4.
- P4: فواصل Progress وReview وGamification scoring منفذة عبر PR #34/#35/#37/#40.
- P5.1–P5.4 مدمجة: WebSocket (#41)، خريطة Frontend (#42)، session (#43)، notification state (#44)، ثم نقل Notifications إلى features/notifications (#46).
- P6.1: Ruff 0.17.3 report-only، 0 diagnostic(s)؛ ESLint لم يُعتمد بعد.
- P6.5: PR #59/#62/#64/#65/#67 مدمجة؛ precache أصبح 8 entries/378.63 KiB بعد خفض يقارب 71.5%. لا يوجد قياس ميداني بعد.
- P6.6: Playwright 1.64.1 + Chromium على production preview مع FastAPI وPostgreSQL وRedis مؤقتة. PR #70 تسجيل/جلسة؛ #73 تقدم الدرس؛ #75 Quiz فارغ وحفظ history؛ #77 صلاحيات وعزل الفصول؛ #80 نشر الدرس؛ #81 اجتياز Quiz عند العتبة؛ #82 إدارة السؤال؛ #84 ClamAV الحقيقي؛ #87 إعادة اتصال WebSocket وتعدد جلسات الإشعارات؛ #88 رسوب البوابة تحت الحد وحفظ المحاولة وHTTP 429 للـ cooldown.
- حسابات الأدوار مؤقتة وترقيتها محصورة في PostgreSQL المحلي lumen_e2e مع guards على المضيف وDATABASE_URL؛ لا endpoint لترقية الأدوار في التطبيق. إعداد ClamAV ورفع الملفات الفعليين خاصان ببيئة CI فقط في PR #84، ولا يتغير إعداد الإنتاج.
- PR #95 مدمج: retry محدود لتهيئة الجلسة عند حدث `online` بعد الفشل المؤقت، مع حماية login/logout واختبارات مركزة؛ لا يعيد إرسال mutations ولا يوفر Offline API.
- PR #97 مدمج: Browser E2E لانقطاع الشبكة وعودتها دون reload. PR #100 مفتوح: Backend coverage 89% و431 passed؛ آخر CI على رأس الوثائق #42223767240 نجح 4/4. PR #102 يقيس Frontend coverage، وPR #101 يختبر SMTP، وPR #103 يضيف API adapter tests. التالي بعد مراجعة/دمج هذه PRs: إعادة قياس coverage على main، ثم اختبارات LTI/OIDC وFiles/ClamAV، وRUM/Core Web Vitals وTypecheck. لا يعني اختبار RTL/LTR اكتمال الترجمة. لا تفتح منفذ ClamAV عامًا ولا تعتبر نجاح خدمة CI إثباتًا لكفاية موارد ماسح الإنتاج.
- سلسلة LTI #16–#23 تحتاج إعادة تأسيس وخطة migration/integration مستقلة؛ لا تدمج مباشرة.
- لا يوجد نشر إنتاجي مثبت.


## ملحق الخطة — تحقق 2026-11-06

- أصبح اختبار استعادة الجلسة بعد عودة الاتصال مدمجًا: PR #95 لمعالجة session bootstrap وPR #97 لاختبار Browser E2E. كلاهما على `main`، وCI بعد PR #97 #42115046453 نجح 4/4.
- أضيف في PR #100 قياس Backend coverage report-only بواسطة `pytest-cov==7.1.0`، مع `--cov-branch` وتقرير XML. لا يُفرض حد أدنى قبل المراجعة.
- تشغيل PR #100 على الرأس `bfc29eb7a02187b7830f30bda5e3a6b46960e6f4` نجح 4/4. Backend **431 passed, 20 warnings**، coverage **89%**؛ `app/tasks.py` أصبحت 92% بعد سبعة اختبارات مركزة.
- PR #100 غير مدمج بعد؛ `main` ما زال عند `fc25ba75987403a85154e55fc70f329d38ee6371`. لا تعتبر قياس PR خط أساس مدمجًا قبل دمج موثق.
- P6 التالية: اختبار SMTP fail-safe وعدم تسريب الرموز، وحالات LTI/OIDC/JWKS/SSRF، ومسارات الملفات وClamAV والمهلات والتنظيف. اختبر باستخدام mocks وخدمات CI مؤقتة، مع عدم فتح ClamAV على الشبكة العامة.
- تبقى RUM/Core Web Vitals الميدانية وقياسات الهاتف/الاتصال البطيء غير مكتملة. P7 غير جاهزة: لا استضافة إنتاجية مثبتة ولا SMTP حقيقي ولا وجهة Restic خارجية.
- لا Microservices، ولا تغيير API/DB/migrations في مرحلة التغطية، ولا تفعيل دفع إلكتروني، ولا موارد مدفوعة.

## تحديث P6 — قياس تغطية Frontend (2026-11-06)

- PR #102 أضاف `@vitest/coverage-v8@5.0.5` المطابق لـ Vitest 5.0.5، وسكربت `npm run test:coverage`، ونطاقًا صريحًا لملفات JS/JSX داخل `frontend/src`. القياس report-only ولا يفرض threshold.
- CI [#42207211737](https://github.com/HVA09/lumen-learning-platform/actions/runs/42207211737) نجح 4/4 على الرأس `58dbf951d478705240e3e5746dee0546967d9e52`: 91 Frontend tests عبر 17 ملفًا؛ statements 31.80%، branches 35.72%، functions 28.82%، lines 32.05%.
- فجوات الاختبار الأوضح: App، AdminDashboard، ContentManager، FilesPanel، وبعض API adapters والمحاكاة. لا تستبعد هذه الوحدات من التغطية؛ أضف اختبارات مركزة حسب المخاطر.
- PR #102 لا يزال مفتوحًا وغير مدمج. PR #100 هو PR المستقل لقياس Backend (89%، 431 passed). لا تعتبر أي رقم baseline مدمجًا قبل تحقق دمج PR المقابل.
- التسلسل التالي: API adapters مع mocks، ثم تدفقات App/Admin/Content/Files؛ بعد ذلك SMTP fail-safe وLTI/OIDC وملفات/ClamAV. تبقى Typecheck وRUM/Core Web Vitals وقياسات الهاتف غير مكتملة.

