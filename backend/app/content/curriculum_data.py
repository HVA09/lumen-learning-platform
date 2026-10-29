"""
المواد والمواضيع الأساسية + خطط الاشتراك الافتراضية — نفس بيانات migrations القديمة (0006/0009/0013)،
مجمّعة هنا عشان الاختبارات وقاعدة بيانات جديدة يقدرون يزرعونها بدون تشغيل كل الـ migrations.
"""

SUBJECTS = [
    {"slug": "math", "name_ar": "الرياضيات", "name_en": "Mathematics", "order_index": 1},
    {"slug": "physics", "name_ar": "الفيزياء", "name_en": "Physics", "order_index": 2},
    {"slug": "programming", "name_ar": "البرمجة", "name_en": "Programming", "order_index": 3},
]

# الترتيب مهم: المتطلّب السابق (prerequisite_slug) لازم يجي قبل الموضوع اللي يعتمد عليه
TOPICS = [
    {
        "subject_slug": "math", "slug": "linear-equations",
        "name_ar": "المعادلات الخطية", "name_en": "Linear Equations",
        "learning_outcomes_ar": ["يحل معادلة خطية بمتغيّر واحد", "يمثّل معادلة خطية بيانيًا"],
        "skill_tags": ["algebra", "linear-functions"],
        "prerequisite_slug": None, "simulation_type": "linear-function", "order_index": 1,
    },
    {
        "subject_slug": "math", "slug": "derivatives-intro",
        "name_ar": "مقدمة في المشتقات", "name_en": "Intro to Derivatives",
        "learning_outcomes_ar": ["يشرح مفهوم معدل التغيّر اللحظي", "يحسب مشتقة دالة كثيرة حدود بسيطة"],
        "skill_tags": ["calculus"],
        "prerequisite_slug": "linear-equations", "simulation_type": "derivative", "order_index": 2,
    },
    {
        "subject_slug": "physics", "slug": "projectile-motion",
        "name_ar": "الحركة المقذوفة", "name_en": "Projectile Motion",
        "learning_outcomes_ar": ["يحلل حركة جسم مقذوف لمركبتين", "يحسب المدى الأفقي والزمن"],
        "skill_tags": ["kinematics", "vectors"],
        "prerequisite_slug": None, "simulation_type": "projectile", "order_index": 1,
    },
    {
        "subject_slug": "physics", "slug": "dc-circuits",
        "name_ar": "الدوائر الكهربائية (تيار مستمر)", "name_en": "DC Circuits",
        "learning_outcomes_ar": ["يطبّق قانون أوم", "يحسب المقاومة المكافئة بدائرة توالي/توازي"],
        "skill_tags": ["electricity"],
        "prerequisite_slug": None, "simulation_type": "circuits-dc", "order_index": 2,
    },
    {
        "subject_slug": "programming", "slug": "python-loops",
        "name_ar": "الحلقات التكرارية بلغة بايثون", "name_en": "Python Loops",
        "learning_outcomes_ar": ["يكتب حلقة for بلغة بايثون", "يستخدم المتغيرات لتجميع نتيجة داخل حلقة"],
        "skill_tags": ["programming", "python"],
        "prerequisite_slug": None, "simulation_type": "python-lab", "order_index": 1,
    },
]

# خطتان افتراضيتان — عدّل stripe_price_id/paypal_plan_id لاحقًا بعد إنشاء الأسعار بحسابك عند مزوّد الدفع
PLANS = [
    {"name": "Free", "price_cents": 0, "currency": "usd", "interval": "month", "is_active": True},
    {"name": "Pro", "price_cents": 1900, "currency": "usd", "interval": "month", "is_active": True},
]
