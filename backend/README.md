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

> ⚠️ **ملاحظة صدق:** اختبارات الـ API المعتمدة على PostgreSQL (`test_classes.py`، `test_content.py`، `test_content_refresh.py`، …) كُتبت لكن **لم تُشغَّل** بالبيئة اللي بُني فيها المشروع (ما فيها PostgreSQL ولا FastAPI). شغّلها عندك قبل الاعتماد عليها، وتوقّع تحتاج تعديلات طفيفة لو ظهر فرق بسيط.

## CI/CD

عند كل push على `main`: تشغيل الاختبارات → بناء صورة Docker → رفعها لـ GitHub
Container Registry → محاولة نشر عبر SSH على سيرفرك.

خطوة النشر (`deploy`) لن تعمل قبل ما تضيف Secrets حقيقية في إعدادات الريبو
(`Settings → Secrets and variables → Actions`): `SERVER_HOST`, `SERVER_USER`,
`SSH_PRIVATE_KEY` — حسب أي سيرفر Cloud تستخدمه (AWS EC2 / Azure VM / GCP Compute
Engine كلها تصلح، لأن الخطوة تتعامل معه كسيرفر Linux عادي عبر SSH).

## قاعدة البيانات (Alembic)

الجداول تُدار عبر migrations. أول تشغيل (والحاويات تسويها تلقائيًا عبر Dockerfile):

```bash
alembic upgrade head
```

الـ migrations الأخيرة:

- `0015_education_upgrade`: تحذف جداول الذكاء الاصطناعي، وتضيف جداول الدروس والأسئلة والاختبارات، وتزرع
  المحتوى الجاهز (آمنة تتكرر: تضيف بس اللي غير موجود).
- `0016_classes_and_analytics`: الفصول (`class_sections`, `class_enrollments`)، وعمود `assignments.class_section_id`
  (فارغ = واجب عام كما كان)، وجدول `question_results` (صف لكل سؤال بكل محاولة) — ويُعبَّأ تلقائيًا من المحاولات
  المُسلَّمة سابقًا فلا تبدأ التحليلات من الصفر.
- `0017_latex_content`: ترقية الدروس والأسئلة والبطاقات الجاهزة لصيغة LaTeX. **تحدّث فقط الصفوف اللي ما زال نصها
  مطابقًا للأصل** — أي درس أو سؤال عدّله معلّم يبقى كما هو، وفهرس الإجابة الصحيحة وترتيب الخيارات لا يتغيران أبدًا.
  لها downgrade يعيد النص الأصلي بنفس الشرط.
- `0018_lti_one_time_auth`: يخزّن حالات OIDC ورموز تبادل LTI كبصمات أحادية الاستخدام مع صلاحية قصيرة.
- `0019_user_token_version`: يضيف إصدار جلسات للحساب ورموز LTI؛ تغيير كلمة المرور أو إعادة تعيينها يبطل الرموز الأقدم.

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
- رفع الملفات يُعالج على دفعات محدودة الحجم، ويُطابق الامتداد وتوقيع الصور/PDF، ويتحقق من بنية DOCX/XLSX وUTF-8 لملفات CSV. لا يتضمن ذلك فحصًا مضادًا للبرمجيات الخبيثة.
- الإيميلات (تأكيد البريد، إعادة تعيين كلمة المرور، ملخص التقدّم الأسبوعي) تُطبع
  باللوق ما لم تضبط SMTP — شغّل السيرفر وشوف رابط التأكيد بالـ terminal مباشرة.
- Two Factor Authentication (TOTP): `/auth/2fa/setup` يرجّع QR code + سر للإدخال اليدوي،
  `/auth/2fa/enable` يفعّله بعد تأكيد رمز صحيح. لو مفعّل، `/auth/login` يرجع 428 لو ما
  أرسلت `totp_code` مع بيانات الدخول.
- Rate Limiting بـ Nginx: 5 طلبات/دقيقة على `/auth/*`، 60 طلب/دقيقة على باقي المسارات.
- رفع الملفات: `POST /files/upload` (صور، PDF، Word، Excel، CSV — حتى `MAX_UPLOAD_SIZE_MB`).
  تُخزَّن على القرص داخل الحاوية (`UPLOAD_DIR`)، مربوطة بـ volume دائم في docker-compose.
- لوحة إدارة (admin فقط): `/admin/stats` (طلاب، معلّمون، دروس، أسئلة، محاولات اختبار،
  واجبات، تسليمات)، `/admin/analytics/daily` (رسوم بيانية آخر N يوم + تصدير CSV)،
  `/admin/users` (عرض/تعديل الدور والتفعيل/حذف — admin ما يقدر يغيّر دوره أو يعطّل
  حسابه بنفسه)، `/admin/logs` (سجل تدقيق للأحداث المهمة).
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
  WebSocket، التوكن كـ query param لأن WebSocket ما يدعم headers مخصصة من المتصفح).
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
أيام). الاسترجاع يستبدل الجداول والكائنات الموجودة في النسخة ويحتاج تأكيدًا صريحًا: `docker compose exec -T backup sh /scripts/restore.sh /backups/backup_XXX.sql.gz --confirm` (تحقق من اسم النسخة قبل التنفيذ).

**المراقبة:**
- `/health` يتحقق فعليًا من اتصال قاعدة البيانات (مو مجرد رد ثابت) — مناسب لفحوصات
  الصحة عند أي منصة استضافة أو load balancer
- `/metrics` يعرض مقاييس Prometheus (عدد الطلبات، زمن الاستجابة...) لو ثبّت المكتبة

## LTI 1.3 (ربط Moodle/Canvas)

⚠️ **تطبيق متوافق مع مواصفة LTI 1.3 الرسمية (IMS Global)، لكن ما اختُبر فعليًا مقابل
منصة LMS حقيقية.** جرّبه بحساب Moodle تجريبي (sandbox) قبل الاعتماد عليه بالإنتاج —
توقّع تحتاج تعديلات طفيفة حسب تفاصيل المنصة اللي تربطها.

**خطوات الربط:**
1. ولّد مفتاح التوقيع الخاص بأداتك: `python scripts/generate_lti_key.py`، وحط الناتج
   بمتغيّر `LTI_TOOL_PRIVATE_KEY` بـ `.env`
2. اضبط `LTI_TARGET_LINK_URI=https://your-domain.com/lti/launch` في بيئة الإنتاج، ثم بلوحة إدارة Moodle أنشئ "External Tool" بصيغة LTI 1.3، واستخدم:
   - Login URL: `https://your-domain.com/lti/login`
   - Redirect URL: `https://your-domain.com/lti/launch`
   - JWKS URL (لأداتك): `https://your-domain.com/lti/jwks`
3. Moodle بيعطيك: `client_id`, `deployment_id`, وروابط auth/token/jwks الخاصة فيه
4. سجّل هذي المعلومات بأداتك عبر `POST /lti/platforms` (admin فقط)
5. من داخل Moodle، أنشئ نشاط "External Tool" يستخدم الأداة المسجّلة — الطلاب يدخلون
   Lumen مباشرة من الكورس بدون تسجيل دخول منفصل

**الأمان:** يجب أن يطابق `target_link_uri` القيمة المضبوطة في `LTI_TARGET_LINK_URI` بالإنتاج، كما يجب أن يطابق claim الموقّع في ID token عنوان حالة OIDC نفسها. يُتحقق من التوقيع، `issuer`, `audience/azp`, `nonce`, `deployment_id`, نوع الرسالة وإصدار LTI ومعرّف resource link ووقت صلاحية الرمز. يُمرر `lti_message_hint` إلى منصة LMS دون تغيير. عند نجاح الإطلاق يُمرر رمز عشوائي قصير العمر وأحادي الاستخدام، ويُستبدل عبر `POST /lti/exchange-code`؛ لا تُمرر JWT tokens في URL. حالة OIDC نفسها تُخزّن كـ hash وتُستهلك مرة واحدة. عناوين `issuer` و`auth_login_url` و`auth_token_url` و`jwks_url` يجب أن تكون HTTPS؛ HTTP مسموح فقط لعناوين loopback في بيئة التطوير/الاختبار.

**ملاحظة:** تصحيح الدرجات التلقائي (Grade Passback / AGS) ما بُني بهذي المرحلة —
المستخدم يدخل ويشتغل بـ Lumen عاديًا، بس درجاته ما ترجع تلقائيًا لسجل درجات Moodle.
