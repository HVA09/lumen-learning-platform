# الحالة التنفيذية لمشروع Lumen Learning Platform

آخر تحقق: 2026-11-02

> هذه لقطة حالة مرتبطة بالـ commits وGitHub Actions أدناه. عند استكمال العمل، حدّث هذا الملف بدل الاعتماد على ملخص محادثة قديم.

## الملخص التنفيذي — الحالة الحالية بعد الدمج (2026-11-02)

- المستودع: [HVA09/lumen-learning-platform](https://github.com/HVA09/lumen-learning-platform) — عام.
- الفرع الافتراضي `main`: محمي، وآخر commit متحقق منه هو merge commit `a945dbb38722b9386332e3528e114f8e641cda05`.
- PR الرئيسي [#4](https://github.com/HVA09/lumen-learning-platform/pull/4) **مُدمج** في 2026-11-02؛ لا تعدّل `main` مباشرة.
- آخر تشغيل CI على `main`: [#523](https://github.com/HVA09/lumen-learning-platform/actions/runs/41510548659)؛ Backend وFrontend/build نجحا، وفشل Gitleaks في 52 كشفًا داخل بيانات الاختبار الوهمية فقط. يجري إصلاح الاستثناءات الدقيقة ومطلوب إعادة تشغيل فحص التاريخ الكامل.
- لا يوجد نشر إنتاجي مثبت حتى الآن.
- فرع المعالجة الحالي: `fix/gitleaks-squash-merge-fingerprints` (PR منفصل سيُنشأ بعد هذا التوثيق).

## نتيجة CI على head الموثق

تشغيل #521 على أحدث head `1cb8dd77fa438b4b099726c86518de25c2a865cd`:

| الوظيفة | النتيجة |
|---|---|
| Backend tests | نجاح — 401 اختبار ناجح، 0 فشل، 20 تحذيرًا |
| Frontend tests and production build | نجاح — 51 اختبارًا عبر 11 ملف اختبار، وبناء الإنتاج نجح |
| Full Git history secret scan | نجاح — لا تسريبات مكتشفة في فحص النطاق والتاريخ الكامل |
| Docker Compose validation | نجاح |
| Migration preservation and upgrade/downgrade regression | نجاح |
| PostgreSQL backup/restore integration | نجاح |
| Restic encrypted backup/restore smoke test | نجاح |

ملاحظة: سجّل بناء الواجهة تحذيرًا غير مانع لحجم بعض الحزم، كما ظهرت تحذيرات اعتماديات منخفضة/متوسطة. النجاح يثبت نتائج CI على commit المحدد؛ لا يعني مراجعة بشرية أو اختبارًا حيًا على خدمة استضافة أو اكتمال النشر.

## ما تم إنجازه في مسار العمل

- دمج إصلاحات الدعوات والحد من محاولات التخمين وإخفاء رمز الدعوة عن الطلاب ضمن فرع PR #4 عبر PR #28.
- تحسينات إدارة الواجبات وتجربة الأخطاء وبعض حدود الطلبات.
- جعل الدفع الإلكتروني معطّلًا افتراضيًا.
- تشديد التحقق من إعدادات الإنتاج.
- إضافة فحص أسرار CI وفحص تاريخ Git كاملًا، مع استثناءات محددة لبصمات قيم اختبار وهمية بعد مراجعتها، لا استثناء واسع لقواعد الكشف أو مجلد الاختبارات.
- توثيق اختبارات النسخ الاحتياطي والاستعادة والترحيل ضمن CI.
- إضافة هذا التوثيق الدائم لتسهيل الاستمرار من عدة أجهزة.

## ما لم يكتمل بعد

1. **دمج PR #4:** اكتمل الدمج في `main` بالـ SHA `a945dbb38722b9386332e3528e114f8e641cda05`. CI #523 أعاد اختبار Backend وFrontend بنجاح، لكنه كشف 52 بصمة Gitleaks لبيانات اختبار وهمية؛ إصلاح البصمات وإعادة فحص التاريخ الكامل قيد التنفيذ.
2. **مراجعة بشرية:** المستخدم يفضل تخطي المراجعة البشرية الاختيارية؛ لا توجد مراجعة بشرية يجب الادعاء بحدوثها. يجب احترام أي قاعدة إلزامية يفرضها GitHub، وعدم تزوير موافقة.
3. **HTTPS والنطاق:** يلزم نطاق وشهادة صالحة وتفعيل إعداد TLS واختبار التجديد وإعادة التوجيه على البيئة المختارة.
4. **ClamAV:** يلزم التحقق من الذاكرة وتوفر الخدمة واستقرار فحص الملفات على المضيف الحقيقي قبل تفعيل رفع الملفات في الإنتاج.
5. **LTI:** يلزم اختبار تكامل حقيقي مع Moodle أو Canvas sandbox قبل تمكينه في الإنتاج.
6. **البريد:** يلزم SMTP فعلي مع TLS وإعدادات المرسل وأسرار خارج المستودع.
7. **النسخ الاحتياطي الخارجي:** اختبارات Restic الحالية آلية/محدودة؛ يلزم إعداد وجهة خارجية حقيقية، ثم إجراء استعادة فعلية منها.
8. **أسرار الإنتاج:** يجب إعداد مفاتيح JWT وTOTP والتكاملات المطلوبة خارج Git وفي إعدادات آمنة للمضيف.
9. **الاستضافة المجانية:** لا يوجد مضيف إنتاج تم التحقق منه بعد لتشغيل كامل المكونات. يجب التحقق من شروط الخطة الحالية، وطلب البطاقة، والذاكرة، والتخزين الدائم، وحدود قاعدة البيانات قبل الاعتماد عليها.
10. **تحسينات غير مانعة:** متابعة تحذيرات Python وحجم حزمة الواجهة وبعض تنبيهات الاعتماديات منخفضة/متوسطة الخطورة، مع إعادة تقييمها عند التحديثات.

## قواعد القرار للمرحلة التالية

- لا تدفع أي رسوم ولا تنشئ موارد قد تتحول إلى فاتورة.
- لا تغيّر `main` مباشرة ولا تحاول تجاوز حمايته.
- قبل أي تعديل، أعد قراءة هذا الملف و`DECISIONS.md` وتحقق من GitHub head وCI الحاليين؛ قد تكون هذه اللقطة أصبحت قديمة.
- بعد أي commit، دوّن SHA ورابط CI وحالة كل job.
- إذا فشل اختبار، أصلح السبب المحدد، ثم أعد تشغيل الفحوصات على أحدث commit. لا تُخفِ فشلًا ولا تُضف استثناءات واسعة.
- لا تقل إن الميزة أو الدمج أو النشر اكتمل إلا بعد التحقق من الدليل المقابل.

## سجل التحديثات

| التاريخ | التغيير |
|---|---|
| 2026-11-02 | إنشاء سجل الحالة الدائم. CI #508 و#509 و#511 و#514 نجحت على commits متعاقبة؛ أحدثها #514 على `6444a618` ويشمل 401 اختبار خلفية و51 اختبار واجهة وبناء الإنتاج وفحص التاريخ الكامل. PR #4 مفتوح وغير مدمج بسبب شرط الموافقة. |


## تحديث مهم — 2026-11-02: حالة الدمج بعد CI #509

- commit المفحوص: `b4bd9c0b716f2303f63c9a1ae70abb75e774520e`.
- [GitHub Actions run #509](https://github.com/HVA09/lumen-learning-platform/actions/runs/41483061442): **نجاح كامل** على هذا commit.
- Backend: **401 passed, 0 failed, 20 warnings**.
- Frontend: **51 passed across 11 test files**، وبناء Vite للإنتاج ناجح.
- Full Git history secret scan: نجح، وأظهر الفحص `no leaks found` في فحص النطاق والتاريخ الكامل.
- اختبارات Docker Compose والتحقق من migrations وbackup/restore وRestic انتهت بنجاح.
- مراجعات PR #4 المسجلة: لا توجد مراجعات (`reviews=[]`).
- جرت محاولة دمج PR #4 باستخدام الـ head المتوقع أعلاه، لكن GitHub رفضها باستجابة HTTP 405: `At least 1 approving review is required by reviewers with write access.`
- لذلك **لم يتم الدمج**، ولا يزال `main` على commit `da33265617b61baaccdea05de5015f73bd1b5d56` عند آخر تحقق. PR #4 مفتوح.
- لم يتم تعطيل حماية الفرع، ولم تُنشأ موافقة وهمية، ولم يحدث نشر إنتاجي.

### بوابة الدمج الحالية

تتطلب حماية `main` موافقة واحدة على الأقل من مراجع لديه صلاحية كتابة، إضافة إلى فحوصات الحالة المطلوبة. المستخدم يفضل تجاوز المراجعة البشرية الاختيارية، لكن إعداد GitHub الحالي يفرض موافقة. اتصال GitHub المتاح لا يملك صلاحية قراءة/تعديل إعدادات الحماية الإدارية (403)، لذلك لا يمكنني تعديل هذه القاعدة عبر الاتصال الحالي.

الخيارات النظامية:
1. يضيف مالك/مسؤول المستودع مراجعًا موثوقًا لديه صلاحية كتابة ويمنح الموافقة المطلوبة؛ أو
2. يغيّر مالك المستودع بنفسه إعداد عدد الموافقات المطلوبة إلى صفر من إعدادات حماية الفرع، إذا قرر قبول تقليل هذه الحماية.

لا تُستخدم أي طريقة التفافية، ولا يُدّعى أن PR مدمج حتى يظهر merge commit على `main`.

| 2026-11-02 | CI #509 اجتاز على `b4bd9c0b`. محاولة الدمج رُفضت بسبب اشتراط موافقة واحدة من مراجع بصلاحية كتابة؛ PR #4 بقي مفتوحًا وmain دون تغيير. |


## أحدث تحقق بعد توثيق عائق الدمج

- [CI #511](https://github.com/HVA09/lumen-learning-platform/actions/runs/41492944574) نجح بالكامل على commit `75a85923ffe66d658ac78e31abdd9003dab18c79`.
- Backend: 401 passed، 0 failed، 20 warnings.
- Frontend: 51 passed عبر 11 ملف اختبار؛ production build ناجح.
- Full-history Gitleaks: نجح، `no leaks found`.
- اختبارات Compose، migrations، PostgreSQL backup/restore، وRestic نجحت.
- يتضمن هذا الـ head توثيق ADR-010 لشرط الموافقة المطلوبة. لم يتغير الكود بين نتيجة #509 وهذه التحديثات التوثيقية.
- أحدث بوابة متوقفة هي الموافقة المطلوبة من GitHub، وليست فشلًا في الاختبارات.


### تمييز commits التوثيق عن تغييرات الكود

- آخر commit للكود الذي تم التحقق منه في CI #511 هو `75a85923ffe66d658ac78e31abdd9003dab18c79`. نتيجة #511: 401 اختبار خلفية، 51 اختبار واجهة، production build، full-history secret scan، واختبارات Compose/migrations/backup/restore ناجحة.
- commits `21f19555` و`58d70523` غيّرت ملفات توثيق فقط ولم تغيّر كود التطبيق.
- مع ذلك، فلتر `pull_request.paths` في GitHub Actions يُقيّم الملفات المتغيرة في فرق PR كاملًا مقابل الفرع الأساسي، وليس آخر commit منفردًا. وبما أن PR #4 يتضمن تغييرات `backend/**` و`frontend/**`، فإن تحديثات التوثيق اللاحقة قد تطلق تشغيل CI جديدًا أيضًا.
- لذلك يجب اعتماد حالة التشغيل المرتبطة بأحدث head الفعلي، وعدم افتراض أن commit توثيقي لا يشغّل CI.


## آخر نقطة تحقق موثقة — CI #514

- [GitHub Actions run #514](https://github.com/HVA09/lumen-learning-platform/actions/runs/41494489575) اكتمل بنجاح على `6444a61850447c9b2d5f3b57e7aee0b7f8aacfb9`.
- Backend: **401 passed, 0 failed, 20 warnings**.
- Frontend: **51 passed across 11 test files**؛ production build passed.
- Full Git history secret scan: **passed**، `no leaks found`.
- Docker Compose، migrations، PostgreSQL backup/restore، وRestic smoke tests: **passed**.
- لا يوجد تغيير في كود التطبيق بين commit الكود الذي فُحص في #511 وhead #514؛ التغييرات بينهما تخص سجل القرارات والحالة والتوثيق. #514 مع ذلك أعاد تشغيل وفحص المسار الكامل للـ PR ونجح.
- PR #4 لا يزال مفتوحًا وغير مدمج؛ GitHub يطلب موافقة واحدة من مراجع بصلاحية كتابة. لا يوجد نشر إنتاجي.


## تحقق أحدث من CI والـ PR — 2026-11-02

- [GitHub Actions run #515](https://github.com/HVA09/lumen-learning-platform/actions/runs/41495156408) نجح على head `abcd3e383a6720dc5b7c5dcfc4c56d7af0e1f6df`.
- Backend: **401 passed, 0 failed, 20 warnings**.
- Frontend: **51 passed across 11 test files**؛ production build passed مع تحذير حجم حزمة غير مانع.
- Full Git history secret scan: **passed**، لا تسريبات مكتشفة.
- Docker Compose، migration preservation/upgrade/downgrade، PostgreSQL backup/restore، وRestic smoke tests: **passed**.
- PR #4 ما زال مفتوحًا وغير مدمج، ومراجعات GitHub الحالية فارغة. الدمج ما زال يتطلب موافقة واحدة من مراجع بصلاحية كتابة وفق ADR-010. `main` لم يتغير، ولم يحدث نشر إنتاجي.
- تقييم الاستضافة المحدث محفوظ في [HOSTING_FEASIBILITY.md](HOSTING_FEASIBILITY.md). الاستنتاج: لا يوجد خيار مؤكد بلا بطاقة يستضيف المكدس الكامل بأمان؛ لا نعطّل فحص ClamAV لتجاوز حدود الذاكرة.


## متابعة مسارات Pull Requests

- أحدث CI مكتمل: [#516](https://github.com/HVA09/lumen-learning-platform/actions/runs/41499900489)، نجاح على head `31079e169d20a5128e31a9390ebded85ca979930`: Backend **401 passed, 20 warnings**؛ Frontend **51 passed / 11 files**؛ production build passed؛ full-history Gitleaks passed؛ migrations وCompose وPostgreSQL backup/restore وRestic smoke tests passed.
- PR #4 مفتوح وغير مدمج؛ يتطلب موافقة واحدة من مراجع بصلاحية كتابة. لا توجد مراجعة مسجلة ولا نشر إنتاجي.
- سلسلة LTI AGS #16–#23 ما زالت مسودات متسلسلة مستقلة، ونتائج CI #424/#426/#427/#429/#432/#433/#436/#440 تاريخية فقط. راجع [PR_STACK_TRIAGE.md](PR_STACK_TRIAGE.md) قبل أي دمج.
- PR #1 أرشيفات ZIP أولية، و#2/#3 معلنان مستبدلين بـ #4، و#5 مبني على فرع استيراد قديم، و#6 وثائق معمارية أقدم تحتاج تحديثًا. لا تدمج أو تغلق هذه الطلبات تلقائيًا.
- تم توثيق قرار عدم إدخال سلسلة LTI المتباعدة مباشرة ضمن ADR-012.


## أحدث تحقق شامل — CI #517 (2026-11-02)

- [GitHub Actions run #517](https://github.com/HVA09/lumen-learning-platform/actions/runs/41500954156) اكتمل بنجاح على head `a1550659f4284a646cbbe8855c979ac6bb4cea63`.
- Backend: **401 passed, 0 failed, 20 warnings**.
- Frontend: **51 passed across 11 test files**؛ production build passed.
- Full Git history secret scan: **passed**؛ لا تسريبات مكتشفة.
- Docker Compose validation، migration preservation/upgrade/downgrade، PostgreSQL backup/restore، وRestic smoke test: **passed**.
- التغييرات في head #517 كانت توثيقية لخريطة PRs وقراراتها؛ لم تتغير شيفرة التشغيل.
- PR #4 مفتوح وغير مدمج، و`main` لا يزال عند `da33265617b61baaccdea05de5015f73bd1b5d56`. لا توجد مراجعة بشرية مسجلة ولا نشر إنتاجي.
- لا تزال بوابة الدمج هي موافقة مراجع واحد لديه صلاحية كتابة وفق ADR-010. لا يتم تجاوزها.

## آخر commit بعد التحقق

- آخر commit موثق: `a1550659f4284a646cbbe8855c979ac6bb4cea63`.
- هذا commit نفسه هو head الذي نجح في CI #517، أي أن سجل الحالة يطابق الرأس المتحقق منه.
- إذا أُضيف أي commit لاحق، يجب فحص CI عليه وتحديث هذه الفقرة.


## أحدث تحقق — CI #518 (2026-11-02)

- [GitHub Actions run #518](https://github.com/HVA09/lumen-learning-platform/actions/runs/41502174758) اكتمل بنجاح على head 9993ad70926b0384f4a10e21d09970e5e52bb25e.
- Backend: **401 passed, 0 failed, 20 warnings**.
- Frontend: **51 passed across 11 files**؛ production build passed.
- Full Git history secret scan: **passed**, no leaks found.
- Docker Compose validation، migration preservation/upgrade/downgrade، PostgreSQL backup/restore، وRestic smoke test: **passed**.
- أحدث تحديثات التوثيق تم اختبارها في #518. لا تغيير في التطبيق runtime ضمن هذه الجولة.
- PR #4 ما زال مفتوحًا وغير مدمج؛ مراجعة GitHub المطلوبة لم تُقدّم، وmain لم يتغير. لا يوجد نشر إنتاجي.

## الخطة المعمارية التالية
- تمت إضافة [ARCHITECTURE_PLAN.md](ARCHITECTURE_PLAN.md) مع توصيف واقعي للبنية الحالية وحدود المجالات وقواعد الاعتماديات.
- التجربة الأولى المقترحة بعد اعتماد خط الأساس: نقل منطق quiz_logic.py الخالص إلى Assessments مع واجهة توافق واختبارات كاملة، دون تغيير API أو قاعدة البيانات أو منطق التصحيح.


## أحدث حالة معتمدة — CI #521 (2026-11-02)

- الفرع: `fix/security-production-hardening`.
- آخر commit متحقق منه: `1cb8dd77fa438b4b099726c86518de25c2a865cd`.
- [GitHub Actions run #521](https://github.com/HVA09/lumen-learning-platform/actions/runs/41504975752): **نجاح كامل** على نفس commit.
- Backend: **402 passed, 0 failed, 20 warnings**. ارتفع العدد من 401 إلى 402 بسبب اختبار قفل TOTP الجديد.
- Frontend: **51 passed across 11 files**؛ production build passed.
- Full Git history secret scan: **passed**؛ no leaks found.
- Docker Compose validation، migration preservation/upgrade/downgrade، PostgreSQL backup/restore، وRestic smoke test: **passed**.
- CI #520 فشل في Gitleaks فقط بسبب 3 بصمات نصوص كلمات مرور اختبار وهمية أضيفت في test fixture. أصلحنا الاختبار لتكوين القيمة من جزأين، وأضفنا **3 fingerprints محددة لهذا commit والملف والأسطر فقط** إلى `.gitleaksignore`. لم نستثنِ مجلد الاختبارات أو أي قاعدة كشف. CI #521 أعاد فحص التاريخ الكامل ونجح.
- إصلاح التطبيق: تسجيل محاولات TOTP غير الصحيحة ضمن `failed_login_attempts` المشتركة، وقفل الحساب مؤقتًا عند بلوغ `MAX_FAILED_LOGIN_ATTEMPTS`، مع إشعار أمني. طلب كلمة المرور الصحيحة بلا TOTP لا يستهلك محاولة.
- الاختبار الجديد `test_invalid_totp_attempts_lock_account` يغطي عدّ المحاولات والقفل ومنع الدخول الصحيح خلال مدة القفل. لم يتغير API أو schema أو migration.
- أضيفت الخطة المعمارية `ARCHITECTURE_PLAN.md` وتوصية Modular Monolith، لكن لم تبدأ عملية نقل وحدات الكود قبل اعتماد PR #4.
- PR #4 لا يزال مفتوحًا وغير مدمج. `main` لا يزال عند آخر commit متحقق منه `da33265617b61baaccdea05de5015f73bd1b5d56`. شرط موافقة مراجع بصلاحية كتابة ما زال قائمًا. لا يوجد نشر إنتاجي.


## تحديث ما بعد الدمج — فشل Gitleaks في CI #523

- PR #4 دُمج عبر squash في commit `a945dbb38722b9386332e3528e114f8e641cda05`.
- CI #523: Backend tests وFrontend tests/build نجحت؛ وظيفة Full Git history secret scan فشلت في خطوة Gitleaks الأولى، ولذلك تخطت خطوة الفحص الشامل اللاحقة.
- فحص سجل الوظيفة كشف 52 بصمة `generic-api-key` على commit الدمج الجديد. تمت مراجعة كل الأسطر المتأثرة في 13 ملفًا تحت `backend/tests/`; جميعها تستخدم كلمة مرور الاختبار المشتركة `StrongPass123` ولا توجد أي نتيجة خارج ملفات الاختبار.
- سبب إعادة ظهورها: squash merge أنشأ SHA جديدًا، لذلك لم تطابق هذه النتائج استثناءات fingerprints السابقة المرتبطة بالـ commits الأصلية.
- الإصلاح المعتمد: إضافة 52 استثناءً محددًا بالـ commit/path/rule/line في `.gitleaksignore` فقط، دون تعطيل Gitleaks أو استثناء مجلد الاختبارات أو تعديل قواعد الكشف. يلزم أن يثبت CI التالي نجاح فحص التاريخ الكامل قبل اعتبار هذه المعالجة مكتملة.
