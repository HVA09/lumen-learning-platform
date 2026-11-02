# تقييم خيارات الاستضافة المجانية لمشروع Lumen

آخر تحقق من المصادر الرسمية: **2026-11-02**.

## النتيجة التنفيذية

لا يوجد بين الخيارات التي تمت مراجعتها مضيف مجاني موثوق بلا بطاقة يضمن تشغيل كامل مكونات Lumen معًا: React/Vite، FastAPI، PostgreSQL، Redis، Celery/Beat، ClamAV، Nginx/TLS، تخزين دائم ونسخ احتياطية خارجية.

**لا نضحّي بالأمان أو سلامة بيانات الطلاب لتناسب خطة مجانية ضعيفة.** يمكن نشر الواجهة الثابتة للمعاينة، أو تشغيل خدمات تجريبية ببيانات اصطناعية، لكن لا نصف ذلك بأنه منصة إنتاجية مكتملة.

## المقارنة الحالية

| الخدمة | الحدود الرسمية المجانية ذات الصلة | ملاءمتها للمشروع |
|---|---|---|
| Cloudflare Pages | الملفات الثابتة: طلبات الأصول مجانية وغير محدودة. Free يسمح حتى 500 build شهريًا و20,000 ملف، حجم الملف الواحد 25 MiB. Pages Functions تدخل ضمن حدود Workers Free: 100,000 طلب/يوم، 128 MB RAM و10 ms CPU. | مرشح جيد لمعاينة واجهة React/Vite الثابتة فقط. Functions ليست مضيف FastAPI أو Celery. |
| Cloudflare Containers | لا توجد موارد Containers مجانية. الاستخدام متاح ضمن Workers Paid الأساسي ($5 شهريًا) وتُحسب موارد الحاويات بحسب التشغيل. | مستبعد بسبب ميزانية صفر. |
| Render Free | Web Service: 512 MB RAM؛ ينام بعد 15 دقيقة من عدم النشاط؛ filesystem مؤقت؛ 750 ساعة مجانية في الشهر. PostgreSQL: 1 GB وينتهي بعد 30 يومًا. مستند البدء يذكر أن النشر الأولي للموارد المجانية لا يحتاج دفعًا. | خيار مقبول لتجربة مؤقتة، لكنه ليس لاستضافة بيانات إنتاجية أو ملفات دائمة. لا يوفر التخزين الدائم على الخطة المجانية. |
| Supabase Free | مشروعان نشطان كحد أقصى؛ قاعدة PostgreSQL 500 MB؛ RAM مشتركة 500 MB؛ 5 GB egress؛ 1 GB file storage. قد يتوقف المشروع عند انخفاض النشاط خلال 7 أيام؛ لا تتوفر تنزيلات النسخ الاحتياطية لمشاريع Free. | جيد لقاعدة تجريبية صغيرة، لكن ليس قاعدة إنتاجية موثوقة بلا خطة نسخ احتياطي مستقلة. لم نثبت شرط البطاقة عند التسجيل؛ لا نفترضه. |
| Neon Free | 100 CU-hour لكل مشروع شهريًا؛ تخزين Postgres 1 GB لكل مشروع؛ 5 GB نقل عام لكل مشروع؛ Autoscaling حتى 2 CU تقريبًا؛ Scale-to-zero بعد 5 دقائق. | مرشح لقاعدة تجريبية، لكن النوم بعد الخمول والحصص الشهرية يجعلانها غير مناسبة لقاعدة إنتاجية تضمن توافرًا مستمرًا. شرط البطاقة غير مؤكد. |
| Upstash Redis Free | 256 MB بيانات؛ 500,000 أمر شهريًا؛ 10 GB bandwidth. مستند Upstash ينص صراحةً على أن قواعد Free لا تتطلب بطاقة. | مرشح مناسب لـRedis محدود في التجارب. انتبه: إدخال بطاقة يحوّل الموارد المجانية إلى خطط مدفوعة بحسب توثيقهم. |
| Koyeb Free | خدمة واحدة مجانية لكل منظمة: 512 MB RAM و0.1 vCPU و2 GB SSD. قاعدة Postgres المجانية 1 GB ومحدودة بخمس ساعات تشغيل فعّال يوميًا. وتصف الوثائق Free Instance بأنها للمعاينة/الهواية لا للإنتاج. | غير كافية للـ API وClamAV والعمال وقاعدة بيانات دائمة. لا نفترض أنها بلا بطاقة دون تحقق أثناء التسجيل. |
| Oracle Cloud Always Free | يتطلب التسجيل بطاقة ائتمان/خصم صالحة للتحقق من الهوية. | مستبعد بسبب عدم توفر بطاقة. |

## متطلبات ClamAV

توثيق ClamAV الرسمي يوصي بـ:
- 3 GiB RAM على الأقل.
- 3–4 GiB RAM لبيئات الخادم والحاويات، وقد تحتاج أكثر عند تشغيل تطبيقات أخرى.
- 5 GiB مساحة قرص حرة للتطبيق، إضافة إلى احتياجات النظام.

هذه المتطلبات تخص ClamAV وحده تقريبًا؛ لذلك لا يمكن اعتبار مضيف 512 MB خيارًا آمنًا لتشغيل Lumen الكامل. تعطيل ClamAV لتجاوز حدود المضيف غير مقبول لأن رفع الملفات يجب أن يفشل مغلقًا في الإنتاج.

## مسار العمل بلا دفع

1. مواصلة التطوير والاختبارات في GitHub Actions دون إنشاء موارد مدفوعة.
2. يمكن تجربة Cloudflare Pages لواجهة ثابتة؛ يجب ضبط رابط API فقط بعد توفر API موثوق. من دون Backend متاح، ستبقى وظائف تسجيل الدخول والبيانات غير متصلة.
3. يمكن تقييم Upstash Free لـRedis التجريبي بعد إنشاء الحساب ومراجعة لوحة الاستخدام، مع عدم إضافة بطاقة.
4. يمكن تقييم Supabase أو Neon كقاعدة بيانات تجريبية فقط بعد التأكد من أن إنشاء الحساب متاح بلا بطاقة، واختبار الاتصال والترحيل والتصدير/الاستعادة.
5. لا تنشر FastAPI/Celery/ClamAV قبل توفر مضيف بموارد كافية، وعامل خلفية مستمر، وتخزين دائم، ونسخة احتياطية خارجية اختُبرت استعادتها.
6. لا تستخدم بيانات طلاب حقيقية في أي بيئة تجريبية؛ ولا تفتح رفع الملفات أو LTI أو البريد قبل اختبارها حيًا على بيئة الهدف.

## القرار الهندسي

**لا يوجد حاليًا خيار مجاني مؤكد بلا بطاقة يصلح لتشغيل المكدس الكامل بأمان.** القرار هو تأجيل نشر الإنتاج الكامل، والاستمرار في التطوير. يمكن نشر معاينة واجهة ثابتة فقط، بشرط توضيح أنها لا تمثل منصة عاملة دون Backend.

## المصادر الرسمية

- Cloudflare Pages limits: https://developers.cloudflare.com/pages/platform/limits/
- Cloudflare Pages Functions pricing: https://developers.cloudflare.com/pages/functions/pricing/
- Cloudflare Workers limits: https://developers.cloudflare.com/workers/platform/limits/
- Cloudflare Containers pricing: https://developers.cloudflare.com/containers/platform/pricing/
- Render Free: https://render.com/docs/free
- Render first deployment (free resources/no payment required): https://render.com/docs/your-first-deploy
- Supabase pricing: https://supabase.com/pricing
- Supabase Free project pausing: https://supabase.com/docs/guides/platform/free-project-pausing
- Supabase production checklist (backup availability): https://supabase.com/docs/guides/deployment/going-into-prod
- Neon Free limits: https://neon.com/docs/introduction/pro-plan
- Neon Free plan quota details: https://neon.com/docs/introduction/free-plan
- Upstash Redis pricing: https://upstash.com/pricing/redis
- Upstash payment-method rules: https://upstash.com/docs/common/account/add-payment-method
- Koyeb instance sizes: https://www.koyeb.com/docs/reference/instances
- Koyeb pricing FAQ: https://www.koyeb.com/docs/faqs/pricing
- Oracle Cloud Free Tier FAQ: https://www.oracle.com/cloud/free/faq/
- ClamAV recommended system requirements: https://docs.clamav.net/
