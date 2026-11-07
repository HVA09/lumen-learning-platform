# دليل اختبار LTI 1.3 وAGS 2.0 مع Moodle أو Canvas

هذا الدليل مخصص لبيئة **Sandbox/Staging**. اختبر Moodle وCanvas كلًّا على حدة، ولا تبدأ بقاعدة بيانات إنتاج أو بطلاب حقيقيين.

## 1. عناوين أداة Lumen التي تسجلها داخل LMS

استبدل `<lumen-host>` باسم الدومين العام الذي يصل إليه LMS عبر HTTPS:

| حقل إعداد أداة LTI في LMS | القيمة |
|---|---|
| OIDC / Login Initiation URL | `https://<lumen-host>/lti/login` |
| Redirect URI / Launch URL | `https://<lumen-host>/lti/launch` |
| Target Link URI | `https://<lumen-host>/lti/launch` |
| Public Keyset URL / JWKS | `https://<lumen-host>/lti/jwks` |

يجب أن تكون شهادة HTTPS صالحة وأن تكون كل المسارات متاحة من خادم LMS نفسه، لا من هاتف المسؤول فقط. يجب ألا يعرض `/lti/jwks` قائمة مفاتيح فارغة.

## 2. تجهيز مفاتيح Lumen

1. ولّد مفتاح RSA من مجلد `backend`:

   ```bash
   python scripts/generate_lti_key.py
   ```

2. في ملف `.env` المحلي، انسخ سطري `LTI_TOOL_PRIVATE_KEY` و`LTI_TOOL_KID` اللذين يطبعهما السكربت كما هما؛ صيغة الاقتباس المزدوج تفك تسلسلات `\\n` إلى أسطر PEM فعلية عند قراءة الملف.
3. في لوحة الاستضافة/Secret Manager، ضع محتوى PEM نفسه بأسطره الفعلية (حوّل تسلسلات `\\n` إلى فواصل أسطر حقيقية)، واحفظ `LTI_TOOL_KID` كمتغير منفصل. لا ترفع المفتاح الخاص إلى Git ولا ترسله في المحادثات.
4. اضبط `LTI_TARGET_LINK_URI=https://<lumen-host>/lti/launch`، واستخدم قيمة KID التي ولّدها السكربت. أعد تشغيل خدمة API بعد تحديث الأسرار، ثم افحص `GET /lti/jwks` وتأكد أن `keys` تحتوي مفتاح RSA واحدًا بمعرّف KID المتوقع.

## 3. تسجيل Lumen كأداة في Moodle أو Canvas

في إعداد أداة LTI 1.3 داخل منصة LMS، أدخل عناوين Lumen في الجدول أعلاه، وسجّل/احفظ أداة Lumen وفق نموذج التسجيل الذي تعرضه نسختك من المنصة.

- **Canvas:** أنشئ LTI Developer Key من نوع LTI 1.3، وحدد Initiate Login URL وRedirect URI وTarget Link URI وPublic JWK URL. فعّل صلاحية AGS الخاصة بكتابة الدرجات (`https://purl.imsglobal.org/spec/lti-ags/scope/score`). لأن Lumen لا ينشئ أعمدة Gradebook في هذه الشريحة، ابدأ بأقل الصلاحيات اللازمة لعنصر تقييم أنشأه المدرّس مسبقًا؛ قد تحتاج المنصة إلى صلاحية قراءة Line Items لإرسال lineitem في رسالة الإطلاق.
- **Moodle:** أضف Lumen كـ External Tool باستخدام إعداد LTI Advantage/LTI 1.3، ثم فعّل صلاحية الأداة لكتابة الدرجات في Gradebook. عند إنشاء نشاط External Tool، تأكد من أن خيار السماح للأداة بإضافة درجات مفعّل.

قد تختلف أسماء الحقول ومواضعها بين إصدارات LMS. اعتمد قيم issuer/client_id/deployment/URLs التي تعرضها المنصة نفسها، ولا تخمّن مسارات endpoints.

## 4. تسجيل منصة LMS داخل Lumen

اجمع من إعداد LTI الخاص بالمنصة القيم التالية: issuer، client ID، deployment ID، OIDC authorization/login endpoint، OAuth token endpoint، وPlatform JWKS URL.

باستخدام حساب Lumen إداري، أرسل `POST /lti/platforms`:

```json
{
  "name": "Moodle Sandbox",
  "issuer": "https://<lms-host>",
  "client_id": "<client-id-from-lms>",
  "deployment_id": "<deployment-id-from-lms>",
  "auth_login_url": "https://<lms-host>/<authorization-endpoint>",
  "auth_token_url": "https://<lms-host>/<token-endpoint>",
  "jwks_url": "https://<lms-host>/<platform-jwks-endpoint>"
}
```

استخدم القيم الدقيقة التي توفرها المنصة. نقطة `auth_login_url` هي authorization endpoint وليست رابط صفحة تسجيل دخول بشرية. احتفظ بمعرّف المنصة `id` من الاستجابة؛ ستحتاجه في ربط Resource Link.

## 5. اكتشاف Resource Link وربطه بواجب Lumen

1. أنشئ واجبًا تجريبيًا في Lumen.
2. أنشئ نشاط External Tool/Assignment في LMS واربطه بأداة Lumen، مع تفعيل كتابة الدرجات.
3. افتح النشاط مرة واحدة بحساب مدرّس تجريبي. بعد إطلاق LTI ناجح، يعرض Lumen روابط الموارد التي شاهدها عبر endpoint الإداري `GET /lti/resource-links`. يعرض endpoint معرّف `resource_link_id` وحالة `lineitem_ready` و`score_scope_allowed`، ولا يعرض معرّف الطالب أو عنوان lineitem الخام. لا يظهر المورد جاهزًا لإرسال الدرجات إلا إذا أرسلت المنصة صلاحية score وعنوان lineitem صالحًا على أصل token endpoint المسجل.
4. اختر `resource_link_id` الصحيح واربطه بواجب Lumen عبر `POST /lti/assignment-links`:

   ```json
   {
     "platform_id": 1,
     "assignment_id": 123,
     "resource_link_id": "<resource-link-id-from-discovery>",
     "score_maximum": 100
   }
   ```

   غيّر المعرفات إلى القيم التي أعادتها بيئتك. اجعل `score_maximum` مطابقًا للدرجة القصوى لعنصر Gradebook في LMS. إذا أعاد endpoint الحقل `lineitem_ready=false`، لا تختبر إرسال الدرجات بعد؛ راجع AGS permissions وإعداد نشاط التقييم.

## 6. سيناريو اختبار الدرجة من البداية إلى النهاية

1. افتح نفس نشاط LMS بحساب طالب تجريبي. يجب أن يتم إنشاء ربط مستخدم LTI المحلي أثناء الإطلاق.
2. سلّم إجابة على واجب Lumen المرتبط.
3. قيّم التسليم من حساب المدرّس في Lumen.
4. راقب `GET /lti/grade-events` كمسؤول. يجب أن يظهر حدث بحالة `pending` ثم `sent` بعد أن يلتقطه Celery worker.
5. تحقق من Gradebook داخل LMS: يجب أن تظهر الدرجة بقيمتها الصحيحة نسبةً إلى `score_maximum`.
6. أعد تقييم التسليم مرة ثانية. يجب أن يظهر `grade_version` جديد وأن تصل الدرجة الأخيرة.
7. اختبر فشلًا مضبوطًا في بيئة Sandbox فقط (مثل إيقاف الاتصال بالمنصة مؤقتًا)، ثم تحقق من retry/backoff ومن عدم تخزين تفاصيل الخطأ الخارجية أو الرموز السرية.

يجب أن تكون خدمتا `celery_worker` و`celery_beat` عاملتين. يلتقط beat أحداث outbox كل دقيقة. يحجز Lumen توقيتًا جديدًا ومتزايدًا لكل محاولة إعادة إرسال، ويعلّم أحداث الدرجات الأقدم بأنها استُبدلت عندما يوجد تقييم أحدث. اختبر هذا السلوك لكل مزود في Sandbox قبل الاستخدام الفعلي.

## 7. اختبارات سلبية مطلوبة وتوثيق النتائج

سجّل نتيجة منفصلة لكل LMS والإصدار المستخدم:

- توقيع ID token خاطئ أو issuer/client/deployment غير مطابق: يجب رفض الإطلاق.
- state/nonce منتهي أو معاد الاستخدام: يجب رفض الإطلاق.
- مستخدم غير مربوط ببريد محلي موجود: لا ينبغي ربط الحساب تلقائيًا بالبريد.
- إطلاق بلا AGS score scope أو lineitem من أصل مختلف: لا يصبح المورد جاهزًا.
- مستخدم لم يطلق نفس Resource Link: لا يُنشأ له حدث grade passback.
- درجة أعلى من الحد الأقصى أو mapping غير جاهز: يجب ألا تُرسل.
- فشل token endpoint أو score endpoint: يبقى الحدث قابلًا لإعادة المحاولة مع رسالة خطأ منقحة.

## 8. معايير إغلاق بوابة Sandbox

لا تعتبر تكامل LMS جاهزًا قبل توثيق: نجاح تسجيل الأداة، نجاح OIDC launch، اكتشاف Resource Link، إنشاء mapping، نجاح OAuth client assertion، وصول Score إلى Gradebook، نجاح re-grade، واختبارات الفشل أعلاه. احتفظ بسجلات الطلبات المنقحة ونتائج الاختبار، ولا تحتفظ بـ ID tokens أو access tokens أو private keys في سجلات المشروع.

## مراجع المواصفات الرسمية

- [1EdTech LTI 1.3](https://www.imsglobal.org/spec/lti/v1p3)
- [1EdTech Assignment and Grade Services 2.0](https://www.imsglobal.org/spec/lti-ags/v2p0/)
- [Canvas AGS configuration and grading](https://developerdocs.instructure.com/services/canvas/external-tools/lti/file.assignment_tools)
- [Moodle LTI External Tools](https://docs.moodle.org/502/en/LTI_External_tools)


## ربط التسليم بمورد LMS الأصلي

يخزن Lumen سياق الإطلاق الموثّق (المنصة، deployment، resource link) داخل جلسة المتصفح التي أنشأها تدفق LTI. عند تسليم واجب، لا يُحفظ هدف AGS إلا إذا وجد ربط إداري يطابق العناصر الثلاثة مع واجب Lumen نفسه. عند التقييم أو إعادة التقييم، ينشأ حدث outbox لهذا الربط المحدد فقط. لا يُرسل Lumen الدرجة إلى جميع موارد المستخدم أو جميع موارد الواجب. التسليم العادي من جلسة Lumen غير مرتبطة بـ LTI لا ينشئ حدث AGS.

قبل إعلان نجاح Sandbox، اختبر على الأقل موردين مختلفين مرتبطين بالواجب نفسه وتأكد أن كل تسليم يرسل إلى lineitem للمورد الذي أطلقه فقط. اختبر كذلك التسليم من جلسة Lumen عادية، ويجب ألا ينتج عنه أي grade passback.
