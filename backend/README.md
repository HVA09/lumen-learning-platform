# Lumen Backend

Backend لمنصّة **لومن** التعليمية (رياضيات، فيزياء، برمجة) — مبني بـ FastAPI +
PostgreSQL، مع مصادقة JWT، صلاحيات حسب الدور (طالب/معلّم/admin)، مسار تعلّم
تكيّفي، اختبارات مصحَّحة بالكامل بالسيرفر، **فصول دراسية** برمز دعوة، **تحليل أسئلة** للمعلّم،
محتوى رياضي بـ **LaTeX**، تكرار متباعد للمراجعة، واجبات يقيّمها المعلّم، تحفيز (نقاط وإنجازات)، اختبارات آلية، Docker، Nginx، وCI/CD.

## البنية

```
app/
  main.py          نقطة التشغيل — يجمع كل شيء
  config.py        الإعدادات (من .env)
  database.py      اتصال SQLAlchemy
  dependencies.py  المستخدم الحالي / صلاحية admin / صلاحية معلّم
  models/          جداول DB: User, Subject, Topic, TopicMastery, Lesson, Question,
                   QuizAttempt, ReviewCard, Assignment, UserAchievement...
  schemas/         Pydantic (تحقق من البيانات الداخلة/الخارجة)
  auth/            تشفير كلمات المرور + JWT + مسارات /auth
  routers/         /curriculum /quiz /content /srs /assignments /gamification
                   /reports /admin /users ...
  services/        منطق بحت قابل للاختبار: تصحيح الاختبارات (quiz_logic)، مسار
                   التعلّم (learning_path)، التكرار المتباعد SM-2+
                   (spaced_repetition)، الإنجازات ولوحة المتصدرين (achievements)
  content/         المحتوى التعليمي الجاهز (دروس/أسئلة/بطاقات) ودالة زرعه
                   (seeder.py) — idempotent، آمن يشتغل أكثر من مرة
tests/             pytest (auth + curriculum + quiz + content + assignments +
                   gamification + srs + reports + admin + LTI + منطق بحت)
nginx/nginx.conf   reverse proxy + rate limiting بسيط
.github/workflows/ CI/CD عبر GitHub Actions
Dockerfile, docker-compose.yml
```

## قبل التشغيل — لازم تجهّزه بنفسك

انسخ `.env.example` إلى `.env` واملأ:

- `POSTGRES_PASSWORD` — كلمة مرور قاعدة البيانات
- `JWT_SECRET_KEY` — قيمة عشوائية طويلة (`openssl rand -hex 32`); إعدادات الإنتاج ترفض القيم الافتراضية الضعيفة.
- `TOTP_ENCRYPTION_KEY` — مفتاح Fernet لتشفير أسرار التحقق الثنائي. ولّده باستخدام:
  `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
  ضعه في Secret Manager، واحتفظ بالقيمة نفسها عبر عمليات إعادة النشر والنسخ الاحتياطية؛ فقدان المفتاح يمنع فك أسرار TOTP المشفرة.
  إعدادات الإنتاج ترفض التشغيل إذا كان المفتاح مفقودًا أو غير صالح.

إعداد SMTP والدفع وLTI اختياري، أما مفتاح TOTP فيلزم عند استخدام المصادقة الثنائية.
(الإيميلات تُطبع باللوق، الدفع والـ LTI معطّلين لين تعبّي مفاتيحهم).

## التشغيل محليًا

```bash
cp .env.example .env   # ثم عدّل القيم
docker compose up --build
```

- الـ API يصير متاح عبر Nginx على `http://localhost`
- توثيق تفاعلي (Swagger): `http://localhost:8000/docs` (مباشرة على منفذ FastAPI أثناء التطوير)
- أول تشغيل يزرع المنهج تلقائيًا (3 مواد، 5 مواضيع، 10 دروس، 53 سؤالًا، 30 بطاقة
  مراجعة جاهزة) عبر migration — راجع قسم "قاعدة البيانات" بالأسفل

أهم المسارات:

| المسار | الوصف |
|---|---|
| POST `/auth/register` | تسجيل مستخدم جديد |
| POST `/auth/login` | تسجيل الدخول → access + refresh token |
| GET `/curriculum/subjects` | المواد والمواضيع (عام، بدون توكن) |
| GET `/curriculum/path` | مسار تعلّم الطالب: حالة كل موضوع والمقترح التالي (يحتاج توكن) |
| GET `/curriculum/topics/{id}/lessons` | دروس الموضوع (يحتاج توكن) |
| POST `/curriculum/lessons/{id}/complete` | تسجيل إنهاء درس |
| POST `/quiz/topics/{id}/start` | بدء اختبار تدريبي أو بوابة إتقان (80% للنجاح) |
| POST `/quiz/attempts/{id}/submit` | تسليم الإجابات — التصحيح وحساب الإتقان بالسيرفر بالكامل |
| POST `/content/topics/{id}/questions` | إضافة سؤال لبنك الأسئلة (معلّم/admin) |
| GET `/content/topics/{id}/analytics` | تحليل أسئلة الموضوع: نسبة نجاح كل سؤال وأكثر إجابة خاطئة وتنبيهات للمراجعة (معلّم/admin) |
| POST `/classes` · POST `/classes/join` | المعلّم ينشئ فصلًا برمز دعوة، والطالب ينضم بالرمز |
| GET `/classes/{id}` | قائمة طلاب الفصل ومتوسط إتقان كل واحد (معلّم الفصل/admin) |
| GET `/gamification/leaderboard?class_id=` | لوحة متصدرين محصورة بطلاب فصل واحد |
| GET `/srs/decks` · POST `/srs/decks/{id}/add` | مجموعات بطاقات جاهزة لكل موضوع |
| POST `/assignments` | إنشاء واجب (معلّم/admin) |
| POST `/assignments/{id}/submissions/{id}/grade` | تقييم تسليم طالب يدويًا |
| GET `/gamification/leaderboard` | لوحة المتصدرين (نقاط محسوبة من نشاط تحقّق منه السيرفر) |
| GET `/reports/my-progress` | تقرير تقدّم الطالب الشامل |
| GET `/admin/stats` | إحصائيات المنصة (يحتاج دور admin) |

للدخول في Swagger: نفّذ `/auth/login`، وانسخ `access_token`، والصقه في زر Authorize
(بصيغة `Bearer <التوكن>`).

## ربط الفرونت اند (React + Vite)

- `CORS_ORIGINS` مضبوط افتراضيًا على `http://localhost:5173` (منفذ Vite dev server). في الإنتاج استخدم origins موثوقة بـ HTTPS فقط.
- منفذ API 8000 مربوط افتراضيًا على `127.0.0.1` في docker-compose لتجنّب الوصول العام المباشر؛ اجعل Nginx هو مدخل الشبكة. مشروع الفرونت (`.env.development`
  فيه `VITE_API_BASE_URL=http://localhost:8000`) يوصله بدون أي إعداد إضافي
- عند النشر: حدّث `CORS_ORIGINS` ليشمل دومين الفرونت الحقيقي


## فحص الملفات والحصص

يتضمن `docker-compose.yml` خدمة ClamAV الرسمية (`clamav/clamav:1.4.6_base-debian13-slim`) مع volume دائم لقواعد التواقيع. الإصدار مثبت على فرع LTS لتجنّب انتقالات الإصدارات الرئيسية غير المقصودة؛ راجع تحديثات الأمان وغيّر الوسم بعد اختبار الإصدار الجديد. التطبيق يتصل بها عبر `CLAMAV_HOST=clamav` و`CLAMAV_PORT=3310` ويستخدم بروتوكول `INSTREAM` لإرسال محتوى الملف على دفعات دون مشاركة مسار الملف مع خدمة الفحص. لا تنشر منفذ ClamAV على الإنترنت أو على واجهة المضيف؛ بروتوكول TCP الخاص بـ clamd غير مشفّر ولا يتضمن مصادقة.

تستخدم خدمة التطبيق شرط `service_healthy`، مستفيدةً من فحص الجاهزية المضمّن في صورة ClamAV للتحقق من استجابة `clamd` قبل بدء API. صورة `_base` لا تحتوي على قاعدة التواقيع المسبقة، لذلك تنزّل FreshClam القواعد إلى الـ volume الدائم عند أول تشغيل؛ قد يتأخر أول بدء حتى تكتمل القواعد. خصّص ذاكرة كافية: توثيق ClamAV يوصي بحد أدنى يقارب 3 GiB ويفضّل 4 GiB، وقد يُقتل daemon إذا لم تكفِ الذاكرة. لا تعتبر الخدمة جاهزة للإنتاج على خطة استضافة أقل من ذلك دون قياس واختبار فعلي.

الإعدادات:
- `MALWARE_SCAN_ENABLED=true`: إلزامي في الإنتاج؛ التطبيق يرفض بدء التشغيل بالإنتاج إذا كان معطلاً.
- `CLAMAV_HOST`, `CLAMAV_PORT`, `CLAMAV_TIMEOUT_SECONDS`: عنوان الخدمة الداخلية والمهلة.
- `MAX_USER_STORAGE_MB=100`, `MAX_USER_FILES=100`: الحصص لكل حساب، إضافة إلى حد حجم الملف `MAX_UPLOAD_SIZE_MB=10`.

إذا لم يتوفر ClamAV أو لم يستطع تحليل الملف، يرجع الرفع HTTP 503 ولا تُحفظ بيانات الملف. إذا اكتُشف ملف ضار يرجع HTTP 422، ويُحذف الملف المؤقت ولا يُسجّل كمرفق. في بيئات التطوير والاختبارات يمكن إيقاف الفحص، لكن هذا غير مسموح في إعداد الإنتاج.

## الاختبارات

تحتاج قاعدة بيانات PostgreSQL منفصلة للاختبار:

```bash
pip install -r requirements-dev.txt
export TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ai_backend_test
pytest -v
```

قاعدة الاختبار تُزرع تلقائيًا بالمنهج والمحتوى الجاهز (`conftest.py`)، فما تحتاج
تشغّل migrations يدويًا قبل الاختبارات.

الاختبارات البحتة (بدون قاعدة بيانات: منطق الاختبارات، مسار التعلّم، رموز الدعوة، تحليل الأسئلة،
فحص جودة المحتوى) تشتغل لوحدها بسرعة: `pytest tests/test_quiz_logic.py tests/test_content_lint.py ...`.

**التحقق الآلي الحالي:** ملف `.github/workflows/ci.yml` يشغّل migrations على PostgreSQL 16، واختبارات pytest، واختبار تكامل فعليًا لسكربتات النسخ والاستعادة على قاعدة PostgreSQL مؤقتة مخصّصة في CI. يرفض اختبار الاستعادة أي مضيف غير loopback وأي اسم قاعدة غير `lumen_backup_restore_test`، ولا يعيد استخدام قاعدة موجودة. اختبار النسخ ينشئ أرشيفًا باستخدام `pg_dump`، ثم يحاكي فقدان البيانات ويستعيدها عبر سكربت الاستعادة ويتحقق من الصفوف المسترجعة. كما يشغّل CI اختبارات Vitest وبناء Vite للواجهة. هذه الفحوصات لا تتصل بقاعدة الإنتاج ولا تغني عن تمرين استعادة تشغيلي على بيئة النشر الفعلية.

## CI/CD

الملف `.github/workflows/ci.yml` يشغّل فحوصات عند التغييرات ذات الصلة في الفرع أو طلبات الدمج:
- الواجهة: تثبيت الاعتماديات، اختبارات Vitest، بناء Vite، وتدقيق اعتماديات الإنتاج.
- الخلفية: Python 3.12 مع PostgreSQL 16 وRedis 7، ثم اختبار حفظ بيانات migrations والرجوع عنها، وتمرين نسخ/استعادة فعلي على قاعدة CI مؤقتة باستخدام PostgreSQL client 16، ثم `alembic upgrade head` واختبارات pytest.

**مهم:** هذا workflow لا يبني صورة Docker للنشر، ولا يرفعها إلى GHCR، ولا ينفّذ نشرًا عبر SSH. لا يوجد نشر إنتاج تلقائي ضمن workflow الحالي.

**اعتماديات الواجهة:** ملف `frontend/package-lock.json` هو المرجع الدقيق لشجرة الحزم. يثبت CI إصدار Node.js `22.23.4` ويستخدم `npm ci` بدل حل الإصدارات من جديد مع كل تشغيل. عند تعديل `frontend/package.json`، حدّث lockfile باستخدام إصدار Node نفسه، ثم راجع التغيير وأودع الملفين معًا؛ لا تعدّل lockfile يدويًا.

## قاعدة البيانات (Alembic)

الجداول تُدار عبر migrations. أول تشغيل (والحاويات تسويها تلقائيًا عبر Dockerfile):

```bash
alembic upgrade head
```

الـ migrations الأخيرة:

- `0015_education_upgrade`: تؤرشف جداول محادثات ورسائل واستخدام الذكاء الاصطناعي القديمة بأسماء
  `legacy_ai_*` بدل حذفها، وتحفظ أعمدة حدود الاستخدام وتقييمات AI والمحاكاة القديمة تحت أسماء
  `legacy_*`. تنشئ أعمدة مستقلة لتقييم المعلّم وتعيد التسليمات التي كانت مقيّمة آليًا إلى انتظار
  التقييم اليدوي. يمكن الرجوع إلى `0014_lti` مع استعادة أسماء الجداول والأعمدة والحالات القديمة.
  كما تنشئ جداول الدروس والأسئلة والاختبارات وتزرع المحتوى الجاهز (بشكل idempotent).
- `0016_classes_and_analytics`: الفصول (`class_sections`, `class_enrollments`)، وعمود `assignments.class_section_id`
  (فارغ = واجب عام كما كان)، وجدول `question_results` (صف لكل سؤال بكل محاولة) — ويُعبَّأ تلقائيًا من المحاولات
  المُسلَّمة سابقًا فلا تبدأ التحليلات من الصفر.
- `0017_latex_content`: ترقية الدروس والأسئلة والبطاقات الجاهزة لصيغة LaTeX. **تحدّث فقط الصفوف اللي ما زال نصها
  مطابقًا للأصل** — أي درس أو سؤال عدّله معلّم يبقى كما هو، وفهرس الإجابة الصحيحة وترتيب الخيارات لا يتغيران أبدًا.
  لها downgrade يعيد النص الأصلي بنفس الشرط.
- `0018_lti_one_time_auth`: يخزّن حالات OIDC ورموز تبادل LTI كبصمات أحادية الاستخدام مع صلاحية قصيرة.
- `0019_user_token_version`: يضيف إصدار جلسات للحساب ورموز LTI؛ تغيير كلمة المرور أو إعادة تعيينها يبطل الرموز الأقدم.
- `0020_totp_secret_ciphertext`: يوسّع `users.totp_secret` من 64 إلى 255 حرفًا لاستيعاب Fernet ciphertext؛ لا يغيّر الأسرار القديمة مباشرة. تُرقّى الأسرار النصية القديمة إلى ciphertext عند نجاح رمز TOTP صحيح في التفعيل أو تسجيل الدخول.
- `0021_webhook_idempotency`: ينشئ `processed_webhook_events` ويحفظ معرّف كل حدث Stripe/PayPal تمّت معالجته. قيد فريد على `(provider, provider_event_id)` يمنع تكرار تطبيق الحدث نفسه، ولا تُحفظ أجسام webhook الخام في الجدول.
- `0022_auth_sessions`: ينشئ `auth_sessions` لتتبع جلسات المتصفح بشكل منفصل لكل جهاز، وتخزين بصمة معرّف refresh الحالي فقط، ودعم تدوير الرموز وإبطال الجلسة عند إعادة تشغيل رمز قديم. حذف المستخدم يحذف جلساته عبر FK cascade.

لو عدّلت أي model، ولّد migration جديدة:

```bash
alembic revision --autogenerate -m "وصف التعديل"
alembic upgrade head
```

## ملاحظات

- التسجيل العام ينشئ حسابًا بدور `user` فقط. لإنشاء أول مدير، شغّل بعد تطبيق migrations
  ومن داخل مجلد `backend`: `python -m app.create_admin`. هذا أمر CLI محلي تفاعلي وليس endpoint
  عامًا؛ يرفض إنشاء مدير آخر إذا كان هناك مدير قائم.
- بعد إنشاء المدير، رقِّ حسابات المعلّمين الموثوقين من `/admin/users/{id}` (`PATCH`، بحقل `role`).
- المعلّم (`teacher`) يقدر: ينشئ دروسًا وأسئلة (`/content`)، ينشئ واجبات ويقيّمها
  يدويًا، ويتخطى قفل المواضيع بالمتطلبات السابقة. الـ `admin` عنده نفس صلاحيات
  المعلّم بالإضافة للوحة الإدارة الكاملة.
- الإتقان (mastery) والتقدّم بالمنهج يُحسبان بالكامل بالسيرفر من نتائج اختبارات
  فعلية — ما فيه أي مسار API يقبل نسبة إتقان أو درجة جاهزة من المتصفح.
- اختبار البوابة (gateway) يحتاج 80% فأكثر للاجتياز، وهو الشرط الوحيد لفتح أي
  موضوع يعتمد عليه موضوع آخر كمتطلب سابق. محاولة فاشلة تفرض مهلة 5 دقائق قبل
  إعادة المحاولة (تشجّع على مراجعة الدرس أولًا)، بينما الاختبار التدريبي متاح
  دائمًا بدون قيود.
- **الفصول:** المعلّم ينشئ فصلًا فيحصل على رمز دعوة من 6 خانات (بدون أحرف ملتبسة مثل 0/O و1/I)، والطالب ينضم به
  (غير حساس لحالة الأحرف). الواجب المحصور بفصل لا يراه ولا يسلّمه إلا طلاب ذلك الفصل ومنشئه وadmin، وتجديد
  الرمز يبطل القديم. حذف الفصل يحذف واجباته وتسليماتها. لوحة المتصدرين لفصل معيّن لأعضائه ومعلّمه وadmin فقط.
- **تحليل الأسئلة:** يحتاج 5 إجابات على الأقل لكل سؤال، ويكشف: سؤال لا أحد أجاب عليه صح (غالبًا مفتاح إجابة
  خاطئ)، وسؤال أصعب/أسهل من صعوبته المصنَّفة، وأكثر خيار خاطئ جذبًا للطلاب.
- **محتوى LaTeX:** النصوص تُكتب بصيغة `$...$` للمعادلة داخل السطر، و`$$` على سطر مستقل قبل المعادلة وبعدها للمعادلة
  المنفصلة (`$$x$$` بسطر واحد تُعرض داخل السطر — يمنعه اختبار الجودة). `tests/test_content_lint.py` يفحص التوازن
  والمفاتيح والخيارات وأن معنى الأسئلة لا يتغير بين الإصدارات.
- كل الأسرار تُقرأ من متغيرات بيئة فقط، ولا يوجد أي مفتاح مكتوب داخل الكود.
- أي خطأ غير متوقع يُسجَّل (logging) ويرجع للمستخدم برسالة عامة بدون تفاصيل داخلية.
- تسجيل الدخول محمي من Brute Force: 5 محاولات فاشلة تقفل الحساب 15 دقيقة (قابلة للتعديل).
- تغيير كلمة المرور أو إعادة تعيينها يرفع `token_version` للحساب، فيبطل رموز الوصول والتجديد القديمة، ورمز إعادة التعيين المستخدم، ورموز تبادل LTI التي صدرت قبل التغيير.
- كلمات المرور التي تتجاوز 72 بايت UTF-8 مرفوضة لتفادي اقتطاع bcrypt؛ الحسابات القديمة التي كانت تستخدم كلمات أطول قد تحتاج إلى إعادة تعيين كلمة المرور.
- رفع الملفات يُعالج على دفعات محدودة الحجم، ويُطابق الامتداد والتوقيع وبنية DOCX/XLSX وUTF-8 لملفات CSV، ثم يمرّر المحتوى إلى ClamAV عبر `INSTREAM` قبل تسجيل الملف. فشل/تعذّر الفحص يرفض الرفع (fail closed) عند تفعيل الفحص. في الإنتاج يجب أن يكون `MALWARE_SCAN_ENABLED=true` مع خدمة ClamAV قابلة للوصول؛ لا يسمح الإعداد الإنتاجي بتعطيل الفحص.
- حصص الرفع لكل مستخدم: `MAX_USER_STORAGE_MB` (100 MiB افتراضيًا) و`MAX_USER_FILES` (100 ملف افتراضيًا). تُسلسل عمليات الرفع للمستخدم بقفل صف المستخدم أثناء فحص الحصة وحفظ البيانات الوصفية، لمنع تجاوز الحصة بطلبات متزامنة.
- الإيميلات (تأكيد البريد، إعادة تعيين كلمة المرور، ملخص التقدّم الأسبوعي) تُطبع
  باللوق ما لم تضبط SMTP — شغّل السيرفر وشوف رابط التأكيد بالـ terminal مباشرة.
- Two Factor Authentication (TOTP): `/auth/2fa/setup` يرجّع QR code + سر للإدخال اليدوي،
  لكن القيمة المخزنة في قاعدة البيانات تكون مشفرة بـ Fernet مع بادئة إصدار `fernet:v1:`.
  `/auth/2fa/enable` يفك القيمة ويتحقق من الرمز ثم يحفظها مشفرة. القيم النصية القديمة
  تبقى قابلة للقراءة وتُرقّى بعد تحقق رمز صحيح. لو 2FA مفعّل، `/auth/login` يرجع 428
  لو لم يُرسل `totp_code`. يجب حفظ `TOTP_ENCRYPTION_KEY` كسر دائم خارج قاعدة البيانات؛
  لا يمكن استعادة الأسرار المشفرة بدونه.
- Rate Limiting بـ Nginx: 5 طلبات/دقيقة على `/auth/*`، 60 طلب/دقيقة على باقي المسارات.
- رفع الملفات: `POST /files/upload` (صور، PDF، Word، Excel، CSV — حتى `MAX_UPLOAD_SIZE_MB` للملف). يُفحص الملف بواسطة ClamAV قبل إدخاله إلى قاعدة البيانات. حصص افتراضية: 100 MiB و100 ملف لكل مستخدم؛ اضبط `MAX_USER_STORAGE_MB` و`MAX_USER_FILES`.
  تُخزَّن الملفات النظيفة على القرص داخل الحاوية (`UPLOAD_DIR`)، مربوطة بـ volume دائم في docker-compose. خدمة ClamAV تعمل على شبكة Docker الداخلية، ومنفذ TCP 3310 لا يُنشر على المضيف.
- لوحة إدارة (admin فقط): `/admin/stats` (طلاب، معلّمون، دروس، أسئلة، محاولات اختبار،
  واجبات، تسليمات)، `/admin/analytics/daily` (رسوم بيانية آخر N يوم + تصدير CSV)،
  `/admin/users` (عرض/تعديل الدور والتفعيل/حذف — admin ما يقدر يغيّر دوره أو يعطّل
  حسابه بنفسه)، `/admin/logs` (سجل تدقيق للأحداث المهمة).
- Webhook Idempotency: يتحقق الخادم أولًا من توقيع Stripe أو PayPal، ثم يحفظ معرّف الحدث ضمن سجل دائم. تكرار المعرّف للمزوّد نفسه يرجع `received=true, duplicate=true` دون إعادة منح الاشتراك أو إرسال إشعار التفعيل مرة ثانية. مفتاح التفرد مركّب من اسم المزوّد ومعرّف الحدث، وتغييرات الاشتراك وإيصال الحدث يُحفظان ضمن معاملة قاعدة بيانات واحدة. الحدث الذي لا يمكن ربطه باشتراك بعد يرجع HTTP 503 ولا يُحفظ كحدث مكتمل، ليتمكن المزوّد من إعادة إرساله. الأحداث غير المدعومة ذات التوقيع الصحيح تُسجّل كأحداث متجاهلة حتى لا تتكرر بلا نهاية.
- الاشتراكات: خطتان جاهزتان (Free, Pro). **قبل ما يشتغل الدفع فعليًا** لازم:
  1. تنشئ منتج/سعر بحساب Stripe (أو خطة بحساب PayPal) وتحدّث `stripe_price_id`
     (أو `paypal_plan_id`) بجدول `plans` يدويًا أو عبر migration جديدة
  2. تعبّي `STRIPE_SECRET_KEY`/`STRIPE_WEBHOOK_SECRET` (أو مفاتيح PayPal) بـ `.env`
  3. تضبط webhook بلوحة Stripe/PayPal يشاور على `https://<دومينك>/billing/webhook/stripe`
     (أو `/paypal`)
  جرّب بوضع Sandbox/Test أول قبل أي مفاتيح حقيقية.
- التكرار المتباعد (SRS): خوارزمية SM-2+ (خطوات تعلّم قبل التخرّج لجدول SM-2 الكامل،
  و"leech" للبطاقات اللي تفشل فيها كثير رغم المراجعة). الطالب يقدر يضيف مجموعة
  بطاقات جاهزة لموضوع بضغطة وحدة (`/srs/decks/{topic_id}/add`) أو ينشئ بطاقاته
  الخاصة.
- إشعارات: `/notifications` (عرض/تعليم كمقروء) + `/ws/notifications` (بث فوري عبر
  WebSocket، تتم المصادقة باستخدام Cookie الجلسة `HttpOnly` مع التحقق من `Origin` والجلسة النشطة؛ لا يُرسل JWT في عنوان URL).
  تنطلق تلقائيًا عند: التسجيل، قفل الحساب، تفعيل/إلغاء الاشتراك، تسليم/تقييم واجب،
  بطاقات مراجعة مستحقة (تذكير يومي)، وملخص تقدّم أسبوعي (كلها مع إيميل مرافق).
  ملاحظة: البث الفوري بالذاكرة (in-memory) — يشتغل تمام لنسخة واحدة من التطبيق؛ لو صار
  عندك أكتر من نسخة تحتاج Redis pub/sub بدلها.
- الأداء:
  - GZip لضغط الاستجابات الكبيرة تلقائيًا
  - Redis caching على `/billing/plans` و`/admin/stats` (دقيقة واحدة افتراضيًا)
  - إرسال الإيميل بالخلفية عبر Celery+Redis (خدمة `celery_worker` بـ docker-compose) —
    لو Celery/Redis مو مضبوطين، يرجع تلقائيًا للإرسال المباشر بدون ما يكسر التطبيق
  - `celery_beat` يشغّل مهمتين مجدولتين: ملخص تقدّم أسبوعي (كل أحد)، وتذكير ببطاقات
    مراجعة مستحقة (يوميًا)

## النشر: HTTPS، النسخ الاحتياطي، والمراقبة

**تنبيه قبل الإنتاج:** إعداد Nginx الموجود حاليًا يشغّل HTTP على المنفذ 80 فقط؛ كتلة HTTPS على المنفذ 443 والتحويل من HTTP إلى HTTPS ما زالت معلّقة بالتعليقات. مجرد نشر منفذ 443 في Docker لا يفعّل TLS. قبل استقبال مستخدمين حقيقيين، فعّل TLS في Nginx بعد إصدار شهادة صالحة، أو استخدم proxy/load balancer موثوقًا ينهي TLS أمام التطبيق. لا تعتبر إعداد Compose الحالي جاهزًا للإنتاج عبر HTTPS دون هذه الخطوة.

**HTTPS (Let's Encrypt مجانًا):**
1. عدّل `nginx/nginx.conf`: استبدل placeholder بدومينك بالجزء المعلَّق (تعليمات داخل الملف)
2. شغّل `docker compose up -d nginx` أول (بدون HTTPS بعد)
3. احصل على الشهادة أول مرة:
   ```
   docker compose run --rm certbot certonly --webroot -w /var/www/certbot \
     -d your-domain.com --email you@example.com --agree-tos --no-eff-email
   ```
4. ألغِ التعليق عن جزء HTTPS بـ nginx.conf وشغّل `docker compose restart nginx`
5. خدمة `certbot` بالـ compose تجدّد الشهادة تلقائيًا كل 12 ساعة (تتأكد بس، ما تجدّد إلا قريب من الانتهاء)

**النسخ الاحتياطي:** خدمة `backup` تاخذ نسخة يومية تلقائيًا لمجلد `./backups` (تحتفظ بآخر 7
أيام). **تنبيه إنتاجي:** الأرشيف الحالي مضغوط بـ gzip لكنه غير مشفّر، ومجلد `./backups` موجود على نفس مضيف التشغيل؛ لذلك لا يحمي وحده من فقدان الخادم أو قرصه ولا يحقق نسخة خارج الموقع. قبل الإنتاج يجب إضافة تخزين خارجي مشفّر، وإدارة مفتاح التشفير خارج الخادم، وسياسة صلاحيات واحتفاظ منفصلة، واختبار استعادة دوري. تُبنى النسخة في ملفات مؤقتة خاصة تُنشأ بـ `mktemp`، ثم يُتحقق من سلامة gzip قبل نشر الاسم النهائي بعملية نقل ذرّية؛ فشل `pg_dump` أو الضغط لا يترك ملفًا يبدو كنسخة مكتملة، ولا يحذف النسخ القديمة. أثناء النسخ يلزم توفر مساحة كافية لملف SQL المؤقت والأرشيف المضغوط معًا. الاستعادة تتحقق من أرشيف gzip كاملًا، ثم تفك ضغطه بالكامل إلى ملف مؤقت قبل تشغيل `psql`؛ لذلك يلزم توفر مساحة مؤقتة إضافية بحجم SQL المستعاد. تتطلب الاستعادة تأكيدًا صريحًا لأنها تستبدل الجداول والكائنات الموجودة: `docker compose exec -T backup sh /scripts/restore.sh /backups/backup_XXX.sql.gz --confirm` (تحقق من اسم النسخة قبل التنفيذ). يختبر CI المسارين على قاعدة PostgreSQL مؤقتة منفصلة: ينشئ نسخة حقيقية، يغيّر البيانات، ثم يستعيد النسخة ويتحقق من عودة البيانات الأصلية؛ ولا يلمس هذا الاختبار قاعدة الإنتاج.

## النسخ الخارجي المشفّر (Restic)

تمت إضافة خدمة اختيارية مستقلة مبنية على Restic `0.19.1` مثبتة بإصدار وصورة محددين. الخدمة غير مفعّلة في التشغيل الاعتيادي؛ لا تبدأ إلا عند تشغيل Compose profile باسم `offsite-backup` وبعد توفير عنوان المستودع وكلمة مروره.

**ما الذي تفعله:**
- تقرأ أحدث أرشيف PostgreSQL مكتمل من `./backups` بوضع read-only.
- تتحقق مرة أخرى من سلامة gzip، ثم ترفع الأرشيف إلى مستودع Restic؛ محتوى المستودع مشفّر قبل تخزينه لدى مزوّد التخزين.
- تتجنب إعادة رفع الأرشيف نفسه إذا كان موجودًا بالفعل في المستودع.
- تطبق سياسة الاحتفاظ الافتراضية: 7 نسخ يومية، و4 أسبوعية، و12 شهرية، و3 سنوية، ثم تشغّل فحص سلامة بيانات المستودع الوصفية بعد pruning.
- تعيد المحاولة كل ساعة عند فشل الاتصال أو عدم جاهزية المستودع. لا تحذف النسخ المحلية ولا تغيّر قاعدة البيانات.

**الإعداد اليدوي عند توفر مزوّد التخزين:**

1. أنشئ bucket أو مساحة تخزين خارج خادم Lumen، أو جهّز خادم SFTP مخصصًا للنسخ.
2. أنشئ كلمة مرور قوية لمستودع Restic واحفظ نسخة منها خارج الخادم أيضًا؛ فقدانها يعني عدم القدرة على فك تشفير النسخ:
   ```bash
   mkdir -p secrets
   umask 077
   openssl rand -base64 48 > secrets/restic-password
   chmod 600 secrets/restic-password
   ```
   مجلد `backend/secrets` مستثنى من Git باستثناء ملف `.gitkeep`؛ لا ترفع كلمة المرور إلى المستودع.
3. اضبط `RESTIC_REPOSITORY` في `.env` بعنوان يدعمه Restic. أمثلة:
   - `s3:https://<endpoint>/<bucket>/lumen` لخدمات S3 والمتوافقة معها.
   - `sftp:<user>@<host>:/<path>/lumen` لخادم SFTP؛ يحتاج إعداد مفتاح SSH المعروف والموثوق بشكل منفصل.
   - يمكن استخدام Azure Blob وGoogle Cloud Storage وREST وrclone مع بيانات اعتماد كل مزوّد.
4. لمخازن S3 المتوافقة، أضف `AWS_ACCESS_KEY_ID` و`AWS_SECRET_ACCESS_KEY` إلى ملف `.env` المحلي فقط، مع أقل صلاحيات لازمة على مسار المستودع.
5. هيّئ المستودع مرة واحدة فقط بعد التأكد من قيمة `RESTIC_REPOSITORY`:
   ```bash
   docker compose --profile offsite-backup run --rm --entrypoint restic offsite_backup init
   ```
6. فعّل الخدمة:
   ```bash
   docker compose --profile offsite-backup up -d offsite_backup
   docker compose logs -f offsite_backup
   ```

**استعادة نسخة من المستودع الخارجي:** أنشئ مجلدًا مؤقتًا على خادم موثوق، ثم استخرج أحدث snapshot إليه:
```bash
mkdir -p restore-staging
docker compose --profile offsite-backup run --rm \
  -v "$PWD/restore-staging:/restore" \
  --entrypoint restic offsite_backup restore latest --target /restore
```
ستظهر الملفات المستعادة تحت `restore-staging/backups/`. افحص الأرشيف ثم انقله إلى مجلد النسخ المحلي، وبعدها استخدم سكربت `restore.sh` مع `--confirm` على قاعدة بيانات مستهدفة بعد التأكد من أنها قاعدة الاستعادة المقصودة. لا تختبر هذا الأمر على قاعدة الإنتاج.

**حدود مهمة:**
- هذه الخدمة اختيارية ولا ترسل أي بيانات خارج الخادم قبل أن يجهز المشغّل حساب التخزين والمستودع والسر.
- النسخة المحلية في `./backups` ما زالت غير مشفّرة؛ التشفير مطبق على مستودع Restic الخارجي فقط. يجب حماية قرص الخادم وصلاحيات مجلد النسخ.
- يجب حفظ كلمة مرور Restic وبيانات مزوّد التخزين خارج خادم النسخ، مع إعداد صلاحيات محدودة وسياسة lifecycle/immutability في المزوّد عند توفرها.
- `restic check` الدوري هنا يتحقق من بنية المستودع وفهارسه، ولا يقرأ كل كتل البيانات. يجب تنفيذ فحص بيانات كامل واستعادة تجريبية دورية وفق حجم المستودع.
- نجاح CI يختبر Restic على مستودع محلي مؤقت، لكنه لا يثبت صلاحية بيانات الاعتماد أو الاتصال بمزوّد سحابي لم يتم ربطه بعد.

**المراقبة:**
- `/health` يتحقق فعليًا من اتصال قاعدة البيانات (مو مجرد رد ثابت) — مناسب لفحوصات
  الصحة عند أي منصة استضافة أو load balancer
- `/metrics` يعرض مقاييس Prometheus (عدد الطلبات، زمن الاستجابة...) لو ثبّت المكتبة

## LTI 1.3 ومرحلة التكامل مع Moodle/Canvas

**الحالة الحالية: تنفيذ أولي لتدفق LTI 1.3، وليس تكاملًا إنتاجيًا معتمدًا أو مختبرًا مع LMS حقيقي.**
الموجود في الكود:
- تسجيل منصات LMS وعرضها (admin فقط).
- نقطة JWKS العامة الخاصة بأداة Lumen.
- بدء تدفق OIDC عبر GET/POST `/lti/login`.
- استقبال إطلاق LTI عبر `/lti/launch` والتحقق من توقيع ID token وissuer وaudience/azp وnonce وdeployment_id ونوع الرسالة وإصدار LTI ومعرّف Resource Link ووقت الصلاحية.
- رمز تبادل عشوائي قصير العمر وأحادي الاستخدام عبر `/lti/exchange-code`، ثم إنشاء جلسة متصفح باستخدام Cookies من نوع HttpOnly.
- اختبارات محاكاة تولّد زوج مفاتيح RSA، وتوقّع ID token فعليًا، وتتحقق من تدفق الإطلاق وتبادل الرمز. هذه الاختبارات لا تثبت التوافق الشبكي مع Moodle أو Canvas.

**غير منفّذ بعد:**
- اختبار اتصال وتسجيل حقيقي مع Moodle أو Canvas (sandbox).
- LTI Assignment and Grade Services (AGS) لإرسال الدرجات إلى سجل درجات LMS.
- Names and Role Provisioning Services (NRPS) لجلب عضويات المقرر والأدوار.
- Deep Linking لاختيار محتوى Lumen وإضافته من داخل LMS.
- شهادة توافق رسمية من 1EdTech.

**متطلبات اختبار LMS حقيقي:**
1. نشر Lumen على دومين عام يمكن لمنصة LMS الوصول إليه عبر HTTPS بشهادة صالحة؛ إعداد Nginx الحالي لا يفعّل HTTPS تلقائيًا، لذا راجع قسم HTTPS أعلاه.
2. إنشاء تسجيل External Tool تجريبي في Moodle أو Canvas والحصول على issuer وclient_id وdeployment_id وروابط المصادقة والرموز وJWKS الخاصة بالمنصة.
3. توليد مفتاح أداة Lumen: `python scripts/generate_lti_key.py`، ثم حفظ المفتاح الخاص في Secret Manager عبر `LTI_TOOL_PRIVATE_KEY` وعدم إضافته إلى Git.
4. ضبط `LTI_TARGET_LINK_URI=https://your-domain.com/lti/launch`، وتسجيل بيانات المنصة في Lumen عبر `POST /lti/platforms` باستخدام حساب admin.
5. تنفيذ سيناريوهات إطلاق ناجح وفاشل، وانتهاء nonce/state، وإعادة استخدام رمز التبادل، ثم توثيق النتائج لكل LMS وإصداره.

**ملاحظات أمنية:** يجب أن يطابق `target_link_uri` القيمة المضبوطة في `LTI_TARGET_LINK_URI` بالإنتاج، كما يجب أن يطابق claim الموقّع في ID token عنوان حالة OIDC نفسها. تُخزّن حالة OIDC كبصمة hash وتُستهلك مرة واحدة. لا تُمرّر JWT tokens في URL؛ يستخدم التدفق رمز تبادل قصير العمر وأحادي الاستخدام. عناوين منصة LMS يجب أن تكون HTTPS في الإنتاج، مع رفض عناوين IP/مضيفات الشبكات الداخلية لمنع SSRF.

**خطة LTI Advantage التالية:**
1. تنفيذ AGS v2.0 بصورة منفصلة: حفظ ربط Resource Link/Assignment، الحصول على OAuth 2.0 access token باستخدام client assertion موقّع، ثم إرسال نتيجة الطالب بعد تقييمها وفق صلاحيات AGS والـ line item الصحيح.
2. إضافة سجل إرسال درجات قابل لإعادة المحاولة (idempotent outbox) حتى لا يؤدي انقطاع الشبكة أو إعادة طلب المعلم إلى إرسال درجات متكررة أو فقدها.
3. إضافة اختبارات بروتوكول باستخدام خادم LMS تجريبي، ثم اختبار Moodle وCanvas كلٌّ على حدة.
4. بعد استقرار AGS، دراسة NRPS وDeep Linking حسب احتياج المنتج.

مرجع المواصفات: [LTI 1.3 Core](https://www.imsglobal.org/spec/lti/v1p3)، [LTI Advantage Implementation Guide](https://developers.imsglobal.org/spec/lti/v1p3/impl)، [Assignment and Grade Services v2.0](https://www.imsglobal.org/spec/lti-ags/v2p0/)، [AGS OpenAPI](https://www.imsglobal.org/spec/lti-ags/v2p0/openapi).

## Browser session security

Browser authentication uses server-issued `HttpOnly` access and refresh cookies. The login response intentionally contains no JWT values. The frontend bootstraps a CSRF token through `GET /auth/csrf` and sends it in the `X-CSRF-Token` header on state-changing requests. Each browser/device receives a distinct `auth_sessions` row. Refresh rotates a one-time `jti` stored only as a SHA-256 digest; reuse of a previously rotated refresh token revokes that session. Logout revokes only the active browser session, while password changes and account security events can still invalidate all sessions through `token_version`.

The notification WebSocket authenticates only from the access cookie, validates the active server-side session, and rejects untrusted `Origin` values. Bearer authentication remains available for non-browser API clients; legacy stateless Bearer tokens remain accepted until expiry, while new browser tokens are session-bound. Browser code must not persist JWTs in `localStorage` or put them in URLs.

Cookie configuration:

- `AUTH_COOKIE_SAMESITE=lax` is the default for same-site deployments.
- Set `AUTH_COOKIE_SAMESITE=none` only when the frontend and API are on different sites; production cookies are then marked `Secure` and require HTTPS.
- Keep `CORS_ORIGINS` restricted to the exact trusted frontend origins. Credentialed CORS must never use a wildcard.
