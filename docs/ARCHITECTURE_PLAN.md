# الخطة المعمارية الحالية والمراحل التنفيذية لمنصة Lumen

آخر تحديث: **2026-11-05**  
آخر تغيير برمجي على main: PR #95 عند Squash commit `80be944a39ffd683daa4ee24cabe48a3bd9067c7`. يعيد تهيئة جلسة HttpOnly عند حدث `online` بعد فشل مؤقت، مع تجميع حدث الشبكة أثناء طلب قائم وحماية حالة login/logout من النتائج القديمة. لا يعيد إرسال mutations ولا ينشئ Offline API. CI على PR [#42108841308](https://github.com/HVA09/lumen-learning-platform/actions/runs/42108841308) وبعد الدمج على main [#42113922307](https://github.com/HVA09/lumen-learning-platform/actions/runs/42113922307) نجحا 4/4.
PR #97 مفتوح على `test/p66-browser-session-network-recovery`: يختبر في Chromium فشل أول `GET /users/me` ثم تبديل Offline/Online واستعادة لوحة المتعلم دون reload. التغيير اختبار E2E فقط؛ CI [#42114408046](https://github.com/HVA09/lumen-learning-platform/actions/runs/42114408046) قيد التنفيذ.
PR #39–#46 و#48 و#49 و#51–#59 و#62 و#64–#84 و#87–#89 و#91 و#95 مدمجة (باستثناء PR #55 و#86 المغلقين دون دمج). PR #59/#62/#64 حسّنت code splitting، وPR #65 أضاف Vite preload recovery، وPR #67 قلّص precache من 35 ملفًا/1328.16 KiB إلى 8 ملفات/378.63 KiB. تغطية Browser E2E تشمل الآن التسجيل والجلسة، التقدم والنشر، Quiz وسجل المحاولات وحدّي النجاح والرسوب، وإدارة السؤال، وفحص ClamAV الحقيقي. PR #87 أكمل اختبار تعدد جلسات الإشعارات وإعادة اتصال WebSocket؛ وPR #91 أضاف اختبار تبديل سمات المستند RTL/LTR. المتبقي هو اختبار فقدان الشبكة وعودتها؛ ولا يدل اختبار الاتجاه على اكتمال ترجمة كل النصوص.

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
| P6 | الجودة والأداء والمراقبة | Ruff 0 diagnostics report-only؛ ESLint لم يبدأ بسبب قيد npm registry؛ code splitting في #59/#62/#64، وpreload recovery في #65، وسياسة PWA في #67 خفّضت precache 71.5% إلى 8 entries/378.63 KiB. P6.6 عبر #70/#73/#75/#77/#80/#81/#82/#84/#87/#88/#89/#91: التسجيل والجلسة، التقدم والنشر، Quiz وسجل المحاولات، الأدوار وعزل الفصول، إدارة السؤال، ClamAV الحقيقي، إعادة اتصال WebSocket وتعدد جلسات الإشعارات، ونتيجة بوابة أسفل الحد مع حفظ الرسوب وHTTP 429 للتهدئة (#88)، واختبار Backend يثبت بقاء الموضوع التابع مقفلاً تحت العتبة (#89)، واختبار تبديل اتجاه المستند RTL/LTR (#91)، واستعادة session bootstrap بعد حدث online (#95). CI PR #95 #42108841308 وبعد الدمج على main #42113922307 نجحا 4/4. PR #97 يضيف Browser E2E لعودة الاتصال دون reload (قيد CI)؛ المتبقي: RUM/Typecheck/Coverage وقياس الميدان |
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

- آخر تغيير برمجي على main: PR #95 عند `80be944a39ffd683daa4ee24cabe48a3bd9067c7`. CI على PR #42108841308 وبعد الدمج #42113922307 نجحا 4/4. PR #91 السابق لديه CI بعد الدمج ناجح 4/4 في #42105382640، وPR #89 في #42102276661.
- P4: فواصل Progress وReview وGamification scoring منفذة عبر PR #34/#35/#37/#40.
- P5.1–P5.4 مدمجة: WebSocket (#41)، خريطة Frontend (#42)، session (#43)، notification state (#44)، ثم نقل Notifications إلى features/notifications (#46).
- P6.1: Ruff 0.17.3 report-only، 0 diagnostic(s)؛ ESLint لم يُعتمد بعد.
- P6.5: PR #59/#62/#64/#65/#67 مدمجة؛ precache أصبح 8 entries/378.63 KiB بعد خفض يقارب 71.5%. لا يوجد قياس ميداني بعد.
- P6.6: Playwright 1.64.1 + Chromium على production preview مع FastAPI وPostgreSQL وRedis مؤقتة. PR #70 تسجيل/جلسة؛ #73 تقدم الدرس؛ #75 Quiz فارغ وحفظ history؛ #77 صلاحيات وعزل الفصول؛ #80 نشر الدرس؛ #81 اجتياز Quiz عند العتبة؛ #82 إدارة السؤال؛ #84 ClamAV الحقيقي؛ #87 إعادة اتصال WebSocket وتعدد جلسات الإشعارات؛ #88 رسوب البوابة تحت الحد وحفظ المحاولة وHTTP 429 للـ cooldown؛ #95 استعادة تهيئة الجلسة عند حدث online بعد فشل مؤقت مع اختبارات منع السباقات.
- حسابات الأدوار مؤقتة وترقيتها محصورة في PostgreSQL المحلي lumen_e2e مع guards على المضيف وDATABASE_URL؛ لا endpoint لترقية الأدوار في التطبيق. إعداد ClamAV ورفع الملفات الفعليين خاصان ببيئة CI فقط في PR #84، ولا يتغير إعداد الإنتاج.
- PR #97 مفتوح: Browser E2E لانقطاع الشبكة وعودة الاتصال واسترجاع الجلسة دون reload؛ بانتظار CI والدمج.
- بعد #97: قياسات RUM/Typecheck/Coverage وCore Web Vitals ميدانيًا. لا يعتبر وجود Service Worker دليلًا على أن API/WebSocket تعمل دون اتصال. تحقق PR #91 من تبديل سمات RTL/LTR فقط ولا يثبت اكتمال الترجمة. لا تفتح منفذ ClamAV عامًا ولا تعتبر نجاح خدمة CI إثباتًا لكفاية موارد ماسح الإنتاج.
- سلسلة LTI #16–#23 تحتاج إعادة تأسيس وخطة migration/integration مستقلة؛ لا تدمج مباشرة.
- لا يوجد نشر إنتاجي مثبت.
