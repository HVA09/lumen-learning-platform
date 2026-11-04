# خريطة بنية الواجهة الأمامية — Lumen

> **الغرض:** توثيق الوضع الفعلي للواجهة وحدود Features وShared تدريجيًا، مع التمييز بين الوحدات المنفذة فعليًا والهيكل المقترح لبقية المجالات.

## 1. نطاق الفحص

- المستودع: `HVA09/lumen-learning-platform`.
- خط الأساس الذي فُحصت عليه الملفات: `main` عند commit `ee149a40b144883b0fea34232ae730574d5e5ed7` بعد PR #46.
- التقنية الحالية: React 19 وVite وTailwind CSS وi18next وAxios وVitest وReact Testing Library.
- لا توجد في الاعتماديات الحالية مكتبة Router مخصصة؛ يقرأ `App.jsx` بعض المسارات مباشرة من `window.location.pathname`، وتُفتح أغلب اللوحات من حالة التطبيق.
- الواجهة تدعم العربية والإنجليزية، مع ضبط `dir` إلى RTL أو LTR عبر `useDirection`.

## 2. البنية الحالية كما هي

```text
frontend/src/
├── App.jsx
├── main.jsx
├── i18n.js
├── index.css
├── components/
│   ├── AppHeader.jsx
│   ├── صفحات ولوحات التطبيق
│   └── simulations/
├── features/
│   └── notifications/
│       ├── api/notificationsApi.js
│       ├── components/NotificationBell.jsx (+ test)
│       ├── hooks/useNotifications.js (+ test)
│       ├── hooks/useNotificationsSocket.js (+ test)
│       └── index.js
├── hooks/
│   ├── useDirection.js
│   └── useSession.js
├── lib/
│   ├── api.js
│   └── وحدات API المتبقية حسب المجال
└── test/
    └── setup.js
```

الاختبارات قريبة من المكونات التي تختبرها، مثل `AuthForm.test.jsx` و`QuizPanel.test.jsx` و`ClassesPanel.test.jsx`، مع إعداد مشترك في `src/test/setup.js`.

### خريطة المجالات الحالية

| المجال | واجهة / مكونات حالية | واجهة API الحالية |
|---|---|---|
| التطبيق والجلسة | `App.jsx`, `AppHeader.jsx`, `useSession.js` | `authApi.js`, `usersApi.js`, `api.js` |
| المصادقة | `AuthForm.jsx`, `VerifyEmailPage.jsx`, `ResetPasswordPage.jsx` | `authApi.js` |
| مسار التعلّم والدروس | `LearningPath.jsx`, `TopicPanel.jsx`, `LabPanel.jsx` | `curriculumApi.js` |
| الاختبارات | `QuizPanel.jsx`, `MathText.jsx` | `quizApi.js` |
| إدارة المحتوى | `ContentManager.jsx` | `contentApi.js` |
| الواجبات والفصول | `AssignmentsPanel.jsx`, `ClassesPanel.jsx` | `assignmentsApi.js`, `classesApi.js` |
| المراجعة المتباعدة | `FlashcardReview.jsx` | `srsApi.js` |
| التحفيز ولوحة المتصدرين | `LeaderboardPanel.jsx`, أجزاء من `LearningPath.jsx` | `gamificationApi.js` |
| التقدم والتقارير | `ProgressPanel.jsx` | `reportsApi.js` |
| الملفات | `FilesPanel.jsx` | `filesApi.js` |
| الإدارة | `AdminDashboard.jsx` | `adminApi.js` |
| الاشتراكات | `BillingPanel.jsx`, صفحات النجاح والإلغاء | `billingApi.js` |
| الإشعارات | `features/notifications/components/NotificationBell.jsx` وHooks داخل `features/notifications/hooks/` | `features/notifications/api/notificationsApi.js` |
| المحاكاة | `components/simulations/*` | تُستدعى من واجهة الدرس / المختبر |

هذه الخريطة تصف المسارات الحالية؛ أصبحت الإشعارات Feature مستقلة داخل `features/notifications` بعد PR #46، بينما تبقى إدارة الجلسة في `hooks/useSession.js` وتظل المكونات وصفحات اللوحات الأخرى منظمة أساسًا تحت `components/`.

## 3. الملاحظات المعمارية

1. **App.jsx ما زال منسق التطبيق:** يدير اللغة واللوحات والتنقل وبعض تنبيهات الواجهة. تهيئة الجلسة في `useSession`، أما مكونات الإشعارات وحالتها واتصال WebSocket وطبقة API فتملكها Feature `notifications`. يبقى تخفيف App تدريجيًا دون نقل غير مبرر.
2. **المكونات مسطحة نسبيًا:** معظم المكونات واللوحات في `components/` مباشرة، بينما المحاكاة فقط لها مجلد فرعي واضح.
3. **وحدات API مقسمة حسب المجال بالفعل:** يجب الحفاظ على هذا الفصل، مع إبقاء `lib/api.js` عميل HTTP المشترك ومسؤولًا عن إعداد Axios وCSRF والجلسة ومعالجة 401.
4. **بعض اللوحات تجمع مهامًا متعددة:** مثل إنشاء/تسليم/تقييم الواجبات، وإدارة الفصول والطلاب. لا تُجزّأ إلا بعد رسم تدفق البيانات والاختبارات الحالية.
5. **تغطية الترجمة تحتاج تدقيقًا:** يوجد إعداد مركزي في `i18n.js`، لكن نصوصًا كثيرة في المكونات مكتوبة مباشرة. لا ننقل النصوص أو نبدلها آليًا قبل تحديد مفاتيح الترجمة المطلوبة واختبار العربية والإنجليزية.
6. **لا نضيف Router الآن لمجرد التنظيم:** المسارات الحالية محدودة. ندرس الحاجة إلى Router عند ظهور متطلبات فعلية مثل روابط عميقة للميزات، حماية مسارات متعددة، أو سجل تنقل أكثر تعقيدًا.
7. **المظهر الداكن ليس مكتملًا:** توثيق الواجهة الحالي ينبه إلى أن `ThemeToggle` لا ينفذ تبديلًا حقيقيًا؛ لا نعتبره ميزة جاهزة.

## 4. الهيكل المستهدف تدريجيًا

الهيكل التالي **اتجاه مقترح**، وليس أمرًا لنقل جميع الملفات في تغيير واحد:

```text
src/
├── app/
│   ├── App.jsx                 # تركيب التطبيق فقط
│   ├── session/                # تهيئة الجلسة وحالتها
│   └── layout/                 # الرأس والحاويات العامة عند الحاجة
├── features/
│   ├── auth/
│   ├── learning/
│   ├── quizzes/
│   ├── content/
│   ├── assignments/
│   ├── classes/
│   ├── review/
│   ├── gamification/
│   ├── progress/
│   ├── files/
│   ├── admin/
│   ├── billing/
│   └── notifications/
├── shared/
│   ├── components/             # مكونات عامة حقًا
│   ├── hooks/                  # Hooks لا تملكها ميزة بعينها
│   └── lib/                    # عميل HTTP وأدوات عامة
├── i18n/
└── test/
```

داخل Feature يمكن استخدام `components/` و`hooks/` و`api/` و`utils/` **عند وجود حاجة فعلية**. لا ننشئ مجلدات فارغة أو طبقات وسيطة لا تضيف فصلًا حقيقيًا.

### قواعد الملكية

- كل Feature تملك مكوناتها وحالتها وأدواتها الخاصة.
- لا تستورد Feature داخلية من ملف عشوائي في Feature أخرى؛ التواصل يكون عبر props أو عقد واضح في مستوى التطبيق.
- المكونات العامة فقط تذهب إلى `shared/components`. لا ننقل كل مكون صغير إلى Shared لمجرد إعادة استخدام محتملة.
- عميل Axios وطبقة الجلسة/CSRF يظلان موحدين؛ لا ننشئ عميل HTTP لكل Feature.
- تبقى عقود Backend وواجهات API الحالية كما هي في خطوات التنظيم.
- لا تنقل ملفات كثيرة مع تعديل سلوك وظيفي في commit واحد.

## 5. تسلسل التنفيذ المقترح

| الترتيب | الشريحة | شرط البدء / معيار القبول |
|---|---|---|
| P5.1 | عزل دورة اتصال WebSocket للإشعارات في Hook | مكتمل ومدمج في PR #41؛ commit `9481c7927cd06653c584f3b11faa4e1d842259b9`؛ CI على PR #41 وCI على `main` بعد الدمج نجحا |
| P5.2 | فصل تهيئة الجلسة ومستخدم التطبيق عن `App.jsx` | مكتمل ومدمج في PR #43؛ commit `9a2a23c071f31f8553b3b1eef9f67195f3b08f07`؛ CI على PR #43 وCI على `main` بعد الدمج نجحا |
| P5.3 | استخراج منطق بيانات الإشعارات وعمليات القراءة إلى Hook | مكتمل ومدمج في PR #44؛ commit `aec9584df78009b07c8bed35b48742d7b7a60ede`؛ CI على PR #44 وCI على `main` بعد الدمج نجحا |
| P5.4 | أول نقل محدود إلى `features/` | مكتمل ومدمج في PR #46؛ `features/notifications` أصبح مالك مكونات الإشعارات وHooks وAPI adapter واختباراتها، وCI #41744744642 ناجح |
| P5.5 | فصل اللوحات الكبيرة إلى مكونات أصغر عند الحاجة | الحفاظ على الصلاحيات وتدفق البيانات وسلوك الهاتف |
| P5.6 | تدقيق الترجمة وRTL/LTR | اختبار تبديل اللغة والاتجاه في النماذج واللوحات والرياضيات والمحتوى |
| P5.7 | تحسين المكونات المشتركة | نقل ما ثبتت مشاركته فعلًا، مع اختبارات مستقلة |

دُمجت شرائح P5.1–P5.4 في `main`: PR #41 ثم PR #43 ثم PR #44 ثم PR #46. في P5.4 نُقلت Feature الإشعارات بعد تحديد import graph والملكية والاختبارات؛ نجحت جميع وظائف CI على رأس PR #46، بينما كان CI بعد الدمج على `main` #41745646366 جاريًا عند آخر تحقق.

## 6. بوابات القبول لكل شريحة

- اختبار Vitest للمكوّن أو Hook المتأثر، ثم مجموعة Frontend كاملة.
- نجاح `npm test` و`npm run build`.
- مراجعة التوافق مع React StrictMode ودورة mount/unmount.
- فحص RTL/LTR على المكونات المتأثرة، لا الاكتفاء باختبار اللغة فقط.
- نجاح Backend tests وdependency audit وGitleaks وCompose وmigrations وbackup/restore في CI المعتمد للمستودع.
- مراجعة diff بحثًا عن تغيير غير مقصود في API أو صلاحيات أو جلسة أو CSRF.
- توثيق commit وPR وCI بعد التنفيذ الفعلي؛ لا نحدّث الحالة باعتبار العمل مكتملًا قبل ذلك.

## 7. ما لا يدخل في هذه الخطة

- لا إعادة كتابة كاملة للواجهة.
- لا تغيير تصميم شامل أو مكتبة UI جديدة ضمن مهمة تنظيم البنية.
- لا نقل جماعي لكل `components/` أو `lib/`.
- لا تخزين JWT في Local Storage أو تجاوز CSRF/HttpOnly.
- لا تغيير API أو قاعدة البيانات أو صلاحيات المستخدمين في PR تنظيمي.
- لا دمج أو تجاوز حماية GitHub لمجرد أن CI أخضر.

## 8. سجل التنفيذ

| التاريخ | العنصر | الحالة |
|---|---|---|
| 2026-11-04 | تحديث خريطة الواجهة بعد P5.4 | تم توثيق ميزة notifications الفعلية في `main` على HEAD `ee149a40b144883b0fea34232ae730574d5e5ed7` بعد PR #46 |
| 2026-11-03 | `useNotificationsSocket` واختباراته | PR #41 مدمج في `main`؛ commit `9481c7927cd06653c584f3b11faa4e1d842259b9`؛ CI PR وCI بعد الدمج ناجحان |
| 2026-11-03 | `useSession` واختباراته | PR #43 مدمج في `main`؛ commit `9a2a23c071f31f8553b3b1eef9f67195f3b08f07`؛ CI PR وCI بعد الدمج ناجحان |
| 2026-11-03 | `useNotifications` وحالة الإشعارات واختباراته | PR #44 مدمج في `main`؛ commit `aec9584df78009b07c8bed35b48742d7b7a60ede`؛ CI على الرأس المعاد تأسيسه وCI بعد الدمج ناجحان |
| التالي | P5.5 — تفكيك لوحة كبيرة عند الحاجة | لا يبدأ قبل تحديد لوحة ذات مسؤولية مركبة؛ ارسم تدفق البيانات واحتفظ بالصلاحيات وسلوك الهاتف والاختبارات |

**تذكير:** نجاح CI في فرع Pull Request لا يعني أن التغيير أصبح جزءًا من `main`، ولا يعني أن الواجهة اختُبرت يدويًا على متصفح حقيقي متصل ببيئة تشغيل منشورة.
