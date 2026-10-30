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
- `JWT_SECRET_KEY` — قيمة عشوائية طويلة (`openssl rand -hex 32`)

باقي القيم (SMTP، الدفع، LTI...) اختيارية — كل شي يشتغل بدونها بوضع تطوير مريح
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

## إنشاء أول مدير بأمان

التسجيل العام ينشئ حسابات عادية فقط؛ لا يمكن لأي زائر الحصول على صلاحية `admin`
بمجرد أن يكون أول من يسجل. بعد تشغيل المنصة وإنشاء حساب المالك من واجهة التسجيل،
نفّذ الأمر التالي من مجلد `backend`:

```bash
docker compose exec app python scripts/promote_initial_admin.py --email owner@example.com
```

اكتب البريد الإلكتروني نفسه عند طلب التأكيد. يرفض الأمر التنفيذ إذا كان هناك مدير
موجود مسبقًا، أو لم يكن الحساب موجودًا/مفعّلًا. يعمل الأمر داخل الخادم ولا يضيف
مسارًا عامًا في API. بعد إنشاء المدير الأول، استخدم لوحة الإدارة لترقية المعلّمين.

## أهم المسارات

| المسار | الوصف |
|---|---|
| POST `/auth/register` | تسجيل مستخدم عادي |
| POST `/auth/login` | تسجيل الدخول → access + refresh token |
| GET `/curriculum/subjects` | المواد والمواضيع (عام، بدون توكن) |
| GET `/curriculum/path` | مسار تعلّم الطالب: حالة كل موضوع والمقترح التالي (يحتاج توكن) |
| GET `/curriculum/topics/{id}/lessons` | دروس الموضوع (يحتاج توكن) |
| POST `/curriculum/lessons/{id}/complete` | تسجيل إنهاء درس |
| POST `/quiz/topics/{id}/start` | بدء اختبار تدريبي أو بوابة إتقان (80% للنجاح) |
| POST `/quiz/attempts/{id}/submit` | تسليم الإجابات — التصحيح وحساب الإتقان بالسيرفر بالكامل |
| POST `/content/topics/{id}/questions` | إضافة سؤال لبنك الأسئلة (معلّم/admin) |
| GET `/content/topics/{id}/analytics` | تحليل أسئلة الموضوع (معلّم/admin) |
| POST `/classes` · POST `/classes/join` | المعلّم ينشئ فصلًا برمز دعوة، والطالب ينضم بالرمز |
| GET `/classes/{id}` | قائمة طلاب الفصل ومتوسط إتقان كل واحد (معلّم الفصل/admin) |
| GET `/gamification/leaderboard?class_id=` | لوحة متصدرين محصورة بطلاب فصل واحد |
| GET `/srs/decks` · POST `/srs/decks/{id}/add` | مجموعات بطاقات جاهزة لكل موضوع |
| POST `/assignments` | إنشاء واجب (معلّم/admin) |
| POST `/assignments/{id}/submissions/{id}/grade` | تقييم تسليم طالب يدويًا |
| GET `/reports/my-progress` | تقرير تقدّم الطالب الشامل |
| GET `/admin/stats` | إحصائيات المنصة (يحتاج دور admin) |

للدخول في Swagger: نفّذ `/auth/login`، وانسخ `access_token`، والصقه في زر Authorize
(بصيغة `Bearer <التوكن>`).

## ربط الفرونت اند (React + Vite)

- `CORS_ORIGINS` مضبوط افتراضيًا على `http://localhost:5173`
- عند النشر: حدّث `CORS_ORIGINS` ليشمل دومين الفرونت الحقيقي

## الاختبارات

تحتاج قاعدة بيانات PostgreSQL منفصلة للاختبار:

```bash
pip install -r requirements-dev.txt
export TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ai_backend_test
pytest -v
```

قاعدة الاختبار تُزرع تلقائيًا بالمحتوى الجاهز (`conftest.py`).

> ⚠️ اختبارات API المعتمدة على PostgreSQL يجب تشغيلها في بيئة اختبار فعلية قبل اعتماد الإصدار.

## CI/CD

عند كل push على `main`: تشغيل الاختبارات → بناء صورة Docker → رفعها لـ GitHub
Container Registry → محاولة نشر عبر SSH على سيرفرك.

## قاعدة البيانات (Alembic)

```bash
alembic upgrade head
```

المخططات تُدار عبر migrations. عند تعديل model، ولّد migration جديدة:

```bash
alembic revision --autogenerate -m "وصف التعديل"
alembic upgrade head
```

## ملاحظات تشغيلية وأمنية

- المعلّم (`teacher`) ينشئ الدروس والأسئلة والواجبات ويقيّمها؛ المدير يملك صلاحيات الإدارة الكاملة.
- الإتقان والتقدّم يُحسبان على الخادم من نتائج الاختبارات الفعلية.
- كل الأسرار تُقرأ من متغيرات البيئة فقط، ولا تُكتب داخل الكود.
- تسجيل الدخول محمي من Brute Force: 5 محاولات فاشلة تقفل الحساب 15 دقيقة (قابلة للتعديل).
- الإيميلات تُطبع باللوق ما لم تضبط SMTP.
- Two Factor Authentication (TOTP) متاح للحسابات.
- Rate Limiting بـ Nginx: 5 طلبات/دقيقة على `/auth/*`، 60 طلب/دقيقة على باقي المسارات.
- رفع الملفات: `POST /files/upload`، وتخزين دائم عبر Docker volume.
- لوحة الإدارة: الإحصائيات، التحليلات اليومية، إدارة المستخدمين، وسجل التدقيق.
- الدفع يجب اختباره في وضع Sandbox/Test قبل مفاتيح الإنتاج.
- LTI 1.3 لم يُختبر بعد مع منصة LMS حقيقية؛ اختبره في بيئة تجريبية قبل الإنتاج.

## النشر: HTTPS والنسخ الاحتياطي

راجع `nginx/nginx.conf` وخطوات Let's Encrypt أدناه، واختبر استعادة النسخ الاحتياطية
قبل الاعتماد على أي نسخة إنتاجية.

## LTI 1.3

اربط Moodle/Canvas فقط بعد إكمال إعداد مفاتيح LTI والتحقق من التدفق في بيئة اختبار.
