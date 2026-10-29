import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import AppHeader from "./components/AppHeader";
import LearningPath from "./components/LearningPath";
import TopicPanel from "./components/TopicPanel";
import AuthForm from "./components/AuthForm";
import Toast from "./components/Toast";
import useDirection from "./hooks/useDirection";

// مُحمَّلة عند الحاجة فقط (lazy) — كل وحدة تصير ملف منفصل (code splitting)،
// يقلّل حجم الحزمة الأولى اللي يحمّلها أي زائر
const VerifyEmailPage = lazy(() => import("./components/VerifyEmailPage"));
const ResetPasswordPage = lazy(() => import("./components/ResetPasswordPage"));
const AccountSettings = lazy(() => import("./components/AccountSettings"));
const FilesPanel = lazy(() => import("./components/FilesPanel"));
const AdminDashboard = lazy(() => import("./components/AdminDashboard"));
const BillingPanel = lazy(() => import("./components/BillingPanel"));
const ContentManager = lazy(() => import("./components/ContentManager"));
const FlashcardReview = lazy(() => import("./components/FlashcardReview"));
const AssignmentsPanel = lazy(() => import("./components/AssignmentsPanel"));
const ClassesPanel = lazy(() => import("./components/ClassesPanel"));
const LeaderboardPanel = lazy(() => import("./components/LeaderboardPanel"));
const ProgressPanel = lazy(() => import("./components/ProgressPanel"));
const BillingSuccessPage = lazy(() => import("./components/BillingSuccessPage"));
const BillingCancelPage = lazy(() => import("./components/BillingCancelPage"));
const LTICallbackPage = lazy(() => import("./components/LTICallbackPage"));
import { getCurrentUser } from "./lib/usersApi";
import {
  listNotifications,
  markNotificationRead,
  markAllNotificationsRead,
  buildNotificationsWebSocketUrl,
} from "./lib/notificationsApi";
import "./i18n";

function PageLoadingFallback() {
  return (
    <div className="flex h-full items-center justify-center bg-slate-50">
      <p className="text-sm text-slate-400">...</p>
    </div>
  );
}

function ModalLoadingFallback() {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <p className="text-sm text-white">...</p>
    </div>
  );
}

export default function App() {
  const [authed, setAuthed] = useState(!!localStorage.getItem("access_token"));
  const [lang, setLang] = useState("ar");
  const [error, setError] = useState("");
  const [toast, setToast] = useState(null); // { message, type }
  const [currentUser, setCurrentUser] = useState(null);
  const [showAccountSettings, setShowAccountSettings] = useState(false);
  const [showFiles, setShowFiles] = useState(false);
  const [showAdmin, setShowAdmin] = useState(false);
  const [showBilling, setShowBilling] = useState(false);
  const [showFlashcards, setShowFlashcards] = useState(false);
  const [showAssignments, setShowAssignments] = useState(false);
  const [showClasses, setShowClasses] = useState(false);
  const [showLeaderboard, setShowLeaderboard] = useState(false);
  const [showProgress, setShowProgress] = useState(false);
  const [contentManagerTopicId, setContentManagerTopicId] = useState(undefined); // undefined = مغلق
  const [activeTopicId, setActiveTopicId] = useState(null);
  const [pathRefreshKey, setPathRefreshKey] = useState(0);
  const [notifications, setNotifications] = useState([]);
  const { i18n } = useTranslation();

  useDirection();

  const isAdmin = currentUser?.role === "admin";
  const isTeacher = currentUser?.role === "teacher" || isAdmin;

  const logout = useCallback(() => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setAuthed(false);
    setError("");
    setCurrentUser(null);
    setShowAccountSettings(false);
    setShowFiles(false);
    setShowAdmin(false);
    setShowBilling(false);
    setNotifications([]);
  }, []);

  // لو أي طلب بأي مكان بالتطبيق رجع 401، نسجّل خروج ونوضّح السبب —
  // قبل كذا كان يصير خروج صامت بدون تفسير
  useEffect(() => {
    const handleUnauthorized = () => {
      logout();
      setToast({ message: "انتهت الجلسة، سجّل الدخول مرة أخرى", type: "error" });
    };
    window.addEventListener("auth:unauthorized", handleUnauthorized);
    return () => window.removeEventListener("auth:unauthorized", handleUnauthorized);
  }, [logout]);

  const refreshCurrentUser = async () => {
    try {
      setCurrentUser(await getCurrentUser());
    } catch {
      // تجاهل بصمت — لوحة الحساب تبقى غير محدّثة لو فشل التحميل فقط
    }
  };

  const refreshNotifications = async () => {
    try {
      setNotifications(await listNotifications());
    } catch {
      // فشل تحميل الإشعارات لا يوقف باقي التطبيق — نتجاهله بصمت
    }
  };

  useEffect(() => {
    if (authed) {
      refreshCurrentUser();
      refreshNotifications();
    }
  }, [authed]);

  // اتصال WebSocket للإشعارات الفورية — يُفتح عند الدخول، ويُغلق عند الخروج
  useEffect(() => {
    if (!authed) return;

    const ws = new WebSocket(buildNotificationsWebSocketUrl());
    ws.onmessage = (event) => {
      const notification = JSON.parse(event.data);
      setNotifications((prev) => [notification, ...prev]);
      setToast({ message: notification.title, type: "success" });
    };

    return () => ws.close();
  }, [authed]);

  const switchLang = (nextLang) => {
    setLang(nextLang);
    i18n.changeLanguage(nextLang);
  };

  const handleMarkNotificationRead = async (id) => {
    try {
      await markNotificationRead(id);
      setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)));
    } catch {
      // تجاهل بصمت — مو حرج
    }
  };

  const handleMarkAllNotificationsRead = async () => {
    try {
      await markAllNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch {
      // تجاهل بصمت — مو حرج
    }
  };

  const handleNewAchievements = (achievements) => {
    achievements.forEach((a, i) => {
      setTimeout(() => setToast({ message: `🏆 فتحت إنجاز: ${a.title_ar}`, type: "success" }), i * 1200);
    });
  };

  const closeTopicPanel = () => {
    setActiveTopicId(null);
    setPathRefreshKey((k) => k + 1); // تحديث حالة المسار (الإتقان، القفل) لو تغيّرت
  };

  const path = window.location.pathname;
  if (path === "/verify-email") {
    return (
      <Suspense fallback={<PageLoadingFallback />}>
        <VerifyEmailPage />
      </Suspense>
    );
  }
  if (path === "/reset-password") {
    return (
      <Suspense fallback={<PageLoadingFallback />}>
        <ResetPasswordPage />
      </Suspense>
    );
  }
  if (path === "/billing/success") {
    return (
      <Suspense fallback={<PageLoadingFallback />}>
        <BillingSuccessPage />
      </Suspense>
    );
  }
  if (path === "/billing/cancel") {
    return (
      <Suspense fallback={<PageLoadingFallback />}>
        <BillingCancelPage />
      </Suspense>
    );
  }
  if (path === "/lti-callback") {
    return (
      <Suspense fallback={<PageLoadingFallback />}>
        <LTICallbackPage />
      </Suspense>
    );
  }

  if (!authed) {
    return (
      <>
        <AuthForm
          onAuthenticated={() => {
            setAuthed(true);
            setToast({ message: "تم تسجيل الدخول بنجاح", type: "success" });
          }}
        />
        <Toast message={toast?.message} type={toast?.type} onDismiss={() => setToast(null)} />
      </>
    );
  }

  return (
    <div className="flex h-full flex-col bg-slate-50 text-slate-900">
      <AppHeader
        lang={lang}
        setLang={switchLang}
        onLogout={logout}
        onOpenAccount={() => setShowAccountSettings(true)}
        onOpenFiles={() => setShowFiles(true)}
        onOpenAdmin={() => setShowAdmin(true)}
        onOpenBilling={() => setShowBilling(true)}
        onOpenFlashcards={() => setShowFlashcards(true)}
        onOpenAssignments={() => setShowAssignments(true)}
        onOpenClasses={() => setShowClasses(true)}
        onOpenLeaderboard={() => setShowLeaderboard(true)}
        onOpenProgress={() => setShowProgress(true)}
        onOpenContent={() => setContentManagerTopicId(null)}
        isAdmin={isAdmin}
        isTeacher={isTeacher}
        notifications={notifications}
        onMarkNotificationRead={handleMarkNotificationRead}
        onMarkAllNotificationsRead={handleMarkAllNotificationsRead}
      />

      {error && (
        <div className="mx-4 mt-3 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <LearningPath key={pathRefreshKey} onSelectTopic={setActiveTopicId} />

      <Toast message={toast?.message} type={toast?.type} onDismiss={() => setToast(null)} />

      {activeTopicId && (
        <TopicPanel
          topicId={activeTopicId}
          onClose={closeTopicPanel}
          isTeacher={isTeacher}
          onManageContent={(topicId) => {
            closeTopicPanel();
            setContentManagerTopicId(topicId);
          }}
          onAchievements={handleNewAchievements}
        />
      )}

      {showAccountSettings && (
        <Suspense fallback={<ModalLoadingFallback />}>
          <AccountSettings
            user={currentUser}
            onClose={() => setShowAccountSettings(false)}
            onUserUpdated={refreshCurrentUser}
            onAccountDeleted={logout}
          />
        </Suspense>
      )}

      {showFiles && (
        <Suspense fallback={<ModalLoadingFallback />}>
          <FilesPanel onClose={() => setShowFiles(false)} />
        </Suspense>
      )}

      {showAdmin && (
        <Suspense fallback={<ModalLoadingFallback />}>
          <AdminDashboard currentUserId={currentUser?.id} onClose={() => setShowAdmin(false)} />
        </Suspense>
      )}

      {showBilling && (
        <Suspense fallback={<ModalLoadingFallback />}>
          <BillingPanel onClose={() => setShowBilling(false)} />
        </Suspense>
      )}

      {contentManagerTopicId !== undefined && (
        <Suspense fallback={<ModalLoadingFallback />}>
          <ContentManager
            initialTopicId={contentManagerTopicId}
            onClose={() => setContentManagerTopicId(undefined)}
          />
        </Suspense>
      )}

      {showFlashcards && (
        <Suspense fallback={<ModalLoadingFallback />}>
          <FlashcardReview onClose={() => setShowFlashcards(false)} />
        </Suspense>
      )}

      {showAssignments && (
        <Suspense fallback={<ModalLoadingFallback />}>
          <AssignmentsPanel isTeacher={isTeacher} onClose={() => setShowAssignments(false)} />
        </Suspense>
      )}

      {showClasses && (
        <Suspense fallback={<ModalLoadingFallback />}>
          <ClassesPanel isTeacher={isTeacher} onClose={() => setShowClasses(false)} />
        </Suspense>
      )}

      {showLeaderboard && (
        <Suspense fallback={<ModalLoadingFallback />}>
          <LeaderboardPanel onClose={() => setShowLeaderboard(false)} />
        </Suspense>
      )}

      {showProgress && (
        <Suspense fallback={<ModalLoadingFallback />}>
          <ProgressPanel onClose={() => setShowProgress(false)} />
        </Suspense>
      )}
    </div>
  );
}
