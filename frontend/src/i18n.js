import i18n from "i18next";
import { initReactI18next } from "react-i18next";

const resources = {
  ar: {
    translation: {
      appName: "لومن",
      appTagline: "منصّتك لتعلّم الرياضيات والفيزياء والبرمجة خطوة بخطوة",
      language: "اللغة",
      arabic: "العربية",
      english: "English",
      logout: "خروج",
    },
  },
  en: {
    translation: {
      appName: "Lumen",
      appTagline: "Your step-by-step platform for math, physics, and programming",
      language: "Language",
      arabic: "العربية",
      english: "English",
      logout: "Logout",
    },
  },
};

i18n.use(initReactI18next).init({
  resources,
  lng: "ar",
  fallbackLng: "ar",
  interpolation: {
    escapeValue: false,
  },
});

export default i18n;
