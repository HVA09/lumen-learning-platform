import LanguageToggle from "./LanguageToggle";
import ThemeToggle from "./ThemeToggle";
import NotificationBell from "./NotificationBell";
import { useTranslation } from "react-i18next";

export default function AppHeader({
  lang,
  setLang,
  onLogout,
  onOpenAccount,
  onOpenFiles,
  onOpenAdmin,
  onOpenBilling,
  onOpenFlashcards,
  onOpenAssignments,
  onOpenClasses,
  onOpenLeaderboard,
  onOpenProgress,
  onOpenContent,
  isAdmin,
  isTeacher,
  notifications,
  onMarkNotificationRead,
  onMarkAllNotificationsRead,
}) {
  const { t } = useTranslation();

  return (
    <header className="flex items-center justify-between border-b border-slate-200 bg-white py-3 pe-4 ps-16 md:ps-4">
      <div>
        <h2 className="text-lg font-semibold">{t("appName")}</h2>
        <p className="hidden text-sm text-slate-500 sm:block">{t("appTagline")}</p>
      </div>
      <div className="flex flex-wrap items-center justify-end gap-2 sm:gap-3">
        <LanguageToggle lang={lang} setLang={setLang} />
        <ThemeToggle />
        <NotificationBell
          notifications={notifications}
          onMarkRead={onMarkNotificationRead}
          onMarkAllRead={onMarkAllNotificationsRead}
        />
        {isAdmin && (
          <button
            onClick={onOpenAdmin}
            className="rounded-full border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400"
          >
            الإدارة
          </button>
        )}
        {(isTeacher || isAdmin) && (
          <button
            onClick={onOpenContent}
            className="rounded-full border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400"
          >
            إدارة المحتوى
          </button>
        )}
        <button
          onClick={onOpenFlashcards}
          className="rounded-full border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400"
        >
          البطاقات
        </button>
        <button
          onClick={onOpenClasses}
          className="rounded-full border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400"
        >
          الفصول
        </button>
        <button
          onClick={onOpenAssignments}
          className="rounded-full border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400"
        >
          الواجبات
        </button>
        <button
          onClick={onOpenLeaderboard}
          className="rounded-full border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400"
        >
          🏆
        </button>
        <button
          onClick={onOpenProgress}
          className="rounded-full border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400"
        >
          تقدّمي
        </button>
        <button
          onClick={onOpenBilling}
          className="rounded-full border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400"
        >
          الاشتراك
        </button>
        <button
          onClick={onOpenFiles}
          className="rounded-full border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400"
        >
          الملفات
        </button>
        <button
          onClick={onOpenAccount}
          className="rounded-full border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400"
        >
          الحساب
        </button>
        <button
          onClick={onLogout}
          className="rounded-full border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400"
        >
          {t("logout")}
        </button>
      </div>
    </header>
  );
}
