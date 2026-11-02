# تقييم خيارات الاستضافة المجانية لمشروع Lumen

آخر تحقق من المصادر الرسمية: **2026-11-02**.

## الخلاصة التنفيذية

الشرط هو استضافة بلا تكلفة ولا بطاقة مع الحفاظ على الأمان. لا يوجد خيار مجاني مؤكد في المصادر التي راجعناها يشغّل المكدس كاملًا: React/Vite، FastAPI، PostgreSQL، Redis، Celery/Beat، ClamAV، Nginx/TLS، تخزين دائم ونسخ احتياطية خارجية.

لا نطلق نسخة الإنتاج على مضيف غير مناسب لمجرد أن اسمه Free. يمكن استخدام بعض الخدمات لمعاينة أجزاء من النظام أو لاختبارات ببيانات اصطناعية فقط.

## مقارنة الخيارات

| الخدمة | حدود الخطة المجانية | القرار |
|---|---|---|
| Cloudflare Pages | استضافة ملفات ثابتة. إنشاء الحساب الموثق يبدأ بالبريد وكلمة المرور. Pages Functions تخضع لحدود Workers Free: 100 ألف طلب يوميًا، و128 MB RAM، و10 ms CPU لكل طلب. | مناسبة لملفات React/Vite فقط، وليست بديلًا عن FastAPI أو Celery. |
| Cloudflare Containers | لا توجد موارد حاويات بالخطة المجانية؛ الحاويات جزء من Workers Paid الأساسي البالغ 5 دولارات شهريًا قبل الاستهلاك الإضافي. | مستبعدة بسبب شرط صفر ميزانية. |
| Render Free | 512 MB RAM لخدمة الويب، إيقاف بعد 15 دقيقة خمولًا، نظام ملفات مؤقت بلا قرص دائم. PostgreSQL المجاني 1 GB وينتهي بعد 30 يومًا ولا يتضمن نسخًا احتياطية. منافذ SMTP الصادرة 25 و465 و587 محظورة. | يصلح لتجربة API مؤقتة فقط؛ لا يصلح لتشغيل المكدس الإنتاجي. |
| Supabase Free | قاعدة PostgreSQL بحجم 500 MB، ذاكرة مشتركة 500 MB، ومشروعان مجانيان. قد يتوقف المشروع عند قلة النشاط على مدى أسبوع. | مرشح لقاعدة تجريبية فقط. شرط عدم طلب بطاقة عند التسجيل لم نثبته من المصدر؛ يجب تأكيده قبل الاعتماد عليه. |
| Neon Free | 1 GB تخزين PostgreSQL لكل مشروع و100 CU-hour شهريًا وفق تحديث 2 أكتوبر 2026. | مرشح لقاعدة تجريبية. شرط عدم طلب البطاقة لم يتم تأكيده في المصدر المفتوح. |
| Upstash Redis Free | 256 MB بيانات، 500 ألف أمر شهريًا، 10 GB نقل شهريًا. وثائق Upstash تنص صراحةً على عدم الحاجة إلى بطاقة للموارد المجانية. | مناسب مبدئيًا لطبقة Redis المحدودة مع مراقبة الاستهلاك. |
| Koyeb Free | خدمة ويب واحدة لكل منظمة: 512 MB RAM، و0.1 vCPU، و2 GB SSD. قاعدة البيانات المجانية محدودة بخمس ساعات تشغيل فعّال يوميًا و1 GB. | لا تناسب API مع ClamAV أو قاعدة بيانات دائمة طوال اليوم. شرط البطاقة غير مؤكد. |
| Oracle Cloud Always Free | يتطلب التسجيل بطاقة ائتمان أو خصم صالحة للتحقق. | مستبعد بسبب عدم توفر بطاقة لدى المستخدم. |

## لماذا لا تكفي هذه الموارد؟

- ClamAV يوصي بحد أدنى يقارب 3 GiB RAM، وبـ3–4 GiB في بيئات الخادم والحاويات، مع مساحة تخزين إضافية. هذا قبل موارد FastAPI وبقية الخدمات.
- تعطيل فحص ClamAV لتجاوز حد الذاكرة يضعف أمان رفع الملفات. التطبيق مضبوط على الفشل المغلق عند غياب الفاحص في الإنتاج؛ يجب الحفاظ على ذلك.
- قاعدة بيانات تنتهي بعد 30 يومًا أو تتوقف عند الخمول ليست مخزنًا ملائمًا لبيانات طلاب حقيقية على المدى الطويل.
- Celery/Beat يحتاج عامل خلفية مستمرًا أو تصميمًا بديلًا واضحًا ومختبرًا.
- Render Free يمنع منافذ SMTP التقليدية المذكورة؛ أي بريد إنتاجي يحتاج مزود API عبر HTTPS يتم التحقق من خطته أولًا.

## المسار المقترح بلا دفع

1. مواصلة التطوير والاختبارات في GitHub Actions دون إنشاء موارد مدفوعة.
2. تقييم Cloudflare Pages لمعاينة ملفات React/Vite الثابتة فقط؛ لا نعرضها كمنصة كاملة قبل ربط API آمن.
3. استخدام Upstash Redis Free فقط إذا اجتاز إنشاء الحساب بلا بطاقة، مع الالتزام بالحدود.
4. اختيار Supabase أو Neon لقاعدة تجريبية فقط بعد التأكد من إمكانية التسجيل بلا بطاقة، ثم اختبار الاتصال والترحيل والنسخ الاحتياطي.
5. عدم نشر FastAPI/Celery/ClamAV قبل وجود مضيف بذاكرة كافية، وتشغيل عامل خلفية، وتخزين دائم ونسخة احتياطية قابلة للاستعادة.
6. لا تستخدم بيانات طلاب حقيقية في البيئة التجريبية، ولا تفتح رفع الملفات أو LTI أو البريد قبل الاختبار الحي على بيئة الهدف.

## القرار

لا يوجد نشر إنتاجي كامل بلا بطاقة يمكن اعتماده بثقة ضمن الخيارات التي تحققت منها. المسار الآمن هو مواصلة التطوير، ثم نشر معاينة جزئية فقط إذا توفرت شروطها، دون وصفها بأنها نسخة إنتاجية مكتملة.

## المصادر الرسمية

- Cloudflare account creation: https://developers.cloudflare.com/fundamentals/account/create-account/
- Cloudflare Workers limits: https://developers.cloudflare.com/workers/platform/limits/
- Cloudflare Pages Functions pricing: https://developers.cloudflare.com/pages/functions/pricing/
- Cloudflare Containers pricing: https://developers.cloudflare.com/containers/platform/pricing/
- Render Free: https://render.com/docs/free
- Render pricing: https://render.com/pricing
- Supabase pricing: https://supabase.com/pricing
- Supabase free project pausing: https://supabase.com/docs/guides/platform/free-project-pausing
- Neon Free plan update (2026-10-02): https://neon.com/blog/neon-free-plan-1-gb-per-project
- Upstash Redis pricing: https://upstash.com/pricing/redis
- Upstash payment method: https://upstash.com/docs/common/account/add-payment-method
- Koyeb instances: https://www.koyeb.com/docs/reference/instances
- Koyeb pricing FAQ: https://www.koyeb.com/docs/faqs/pricing
- Oracle Cloud Free Tier FAQ: https://www.oracle.com/cloud/free/faq/
- ClamAV recommended requirements: https://docs.clamav.net/
- ClamAV Docker memory guidance: https://docs.clamav.net/manual/Installing/Docker.html
