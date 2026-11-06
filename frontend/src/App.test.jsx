import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "./i18n";
import App from "./App";

const mocks = vi.hoisted(() => ({
  session: {
    authenticated: false,
    authReady: true,
    currentUser: null,
    markAuthenticated: vi.fn(),
    logout: vi.fn(),
    refreshCurrentUser: vi.fn(),
  },
  notifications: {
    notifications: [],
    addNotification: vi.fn(),
    markNotificationRead: vi.fn(),
    markAllNotificationsRead: vi.fn(),
  },
  sessionExpired: null,
  incomingNotification: null,
  notificationsEnabled: null,
  socketEnabled: null,
}));

vi.mock("./hooks/useSession", () => ({
  default: ({ onSessionExpired }) => {
    mocks.sessionExpired = onSessionExpired;
    return mocks.session;
  },
}));

vi.mock("./hooks/useDirection", () => ({
  default: vi.fn(),
}));

vi.mock("./features/notifications", () => ({
  useNotifications: ({ enabled }) => {
    mocks.notificationsEnabled = enabled;
    return mocks.notifications;
  },
  useNotificationsSocket: ({ enabled, onNotification }) => {
    mocks.socketEnabled = enabled;
    mocks.incomingNotification = onNotification;
  },
}));

vi.mock("./components/AuthForm", () => ({
  default: ({ onAuthenticated }) => (
    <button onClick={onAuthenticated}>fake-authenticate</button>
  ),
}));

vi.mock("./components/AppHeader", () => ({
  default: ({
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
  }) => (
    <header
      data-testid="app-header"
      data-is-admin={String(isAdmin)}
      data-is-teacher={String(isTeacher)}
      data-lang={lang}
    >
      <button onClick={setLang.bind(null, "en")}>switch-language</button>
      <button onClick={onOpenAccount}>open-account</button>
      <button onClick={onOpenFiles}>open-files</button>
      <button onClick={onOpenAdmin}>open-admin</button>
      <button onClick={onOpenBilling}>open-billing</button>
      <button onClick={onOpenFlashcards}>open-flashcards</button>
      <button onClick={onOpenAssignments}>open-assignments</button>
      <button onClick={onOpenClasses}>open-classes</button>
      <button onClick={onOpenLeaderboard}>open-leaderboard</button>
      <button onClick={onOpenProgress}>open-progress</button>
      <button onClick={onOpenContent}>open-content</button>
      <button onClick={onLogout}>logout</button>
    </header>
  ),
}));

vi.mock("./components/LearningPath", () => ({
  default: ({ onSelectTopic }) => (
    <button onClick={() => onSelectTopic(42)}>select-topic</button>
  ),
}));

vi.mock("./components/Toast", () => ({
  default: ({ message, type, onDismiss }) =>
    message ? (
      <div role="status" data-toast-type={type}>
        <span>{message}</span>
        <button onClick={onDismiss}>dismiss-toast</button>
      </div>
    ) : null,
}));

vi.mock("./components/TopicPanel", () => ({
  default: ({ topicId, isTeacher, onClose, onManageContent }) => (
    <section
      data-testid="topic-panel"
      data-topic-id={String(topicId)}
      data-is-teacher={String(isTeacher)}
    >
      <button onClick={onClose}>close-topic</button>
      <button onClick={() => onManageContent(topicId)}>manage-topic-content</button>
    </section>
  ),
}));

vi.mock("./components/AccountSettings", () => ({
  default: ({ user, onClose, onAccountDeleted }) => (
    <section data-testid="account-settings" data-user-id={String(user?.id)}>
      <button onClick={onClose}>close-account</button>
      <button onClick={onAccountDeleted}>delete-account</button>
    </section>
  ),
}));

vi.mock("./components/FilesPanel", () => ({
  default: ({ onClose }) => (
    <section data-testid="files-panel">
      <button onClick={onClose}>close-files</button>
    </section>
  ),
}));

vi.mock("./components/AdminDashboard", () => ({
  default: ({ currentUserId, onClose }) => (
    <section data-testid="admin-dashboard" data-user-id={String(currentUserId)}>
      <button onClick={onClose}>close-admin</button>
    </section>
  ),
}));

vi.mock("./components/BillingPanel", () => ({
  default: ({ onClose }) => (
    <section data-testid="billing-panel">
      <button onClick={onClose}>close-billing</button>
    </section>
  ),
}));

vi.mock("./components/ContentManager", () => ({
  default: ({ initialTopicId, onClose }) => (
    <section
      data-testid="content-manager"
      data-topic-id={initialTopicId == null ? "all" : String(initialTopicId)}
    >
      <button onClick={onClose}>close-content-manager</button>
    </section>
  ),
}));

vi.mock("./components/FlashcardReview", () => ({
  default: ({ onClose }) => <button onClick={onClose}>close-flashcards</button>,
}));
vi.mock("./components/AssignmentsPanel", () => ({
  default: ({ isTeacher, onClose }) => (
    <section data-testid="assignments-panel" data-is-teacher={String(isTeacher)}>
      <button onClick={onClose}>close-assignments</button>
    </section>
  ),
}));
vi.mock("./components/ClassesPanel", () => ({
  default: ({ isTeacher, onClose }) => (
    <section data-testid="classes-panel" data-is-teacher={String(isTeacher)}>
      <button onClick={onClose}>close-classes</button>
    </section>
  ),
}));
vi.mock("./components/LeaderboardPanel", () => ({
  default: ({ onClose }) => <button onClick={onClose}>close-leaderboard</button>,
}));
vi.mock("./components/ProgressPanel", () => ({
  default: ({ onClose }) => <button onClick={onClose}>close-progress</button>,
}));

vi.mock("./components/VerifyEmailPage", () => ({
  default: () => <div data-testid="verify-email-page">verify-email-route</div>,
}));
vi.mock("./components/ResetPasswordPage", () => ({
  default: () => <div data-testid="reset-password-page">reset-password-route</div>,
}));
vi.mock("./components/BillingSuccessPage", () => ({
  default: () => <div data-testid="billing-success-page">billing-success-route</div>,
}));
vi.mock("./components/BillingCancelPage", () => ({
  default: () => <div data-testid="billing-cancel-page">billing-cancel-route</div>,
}));
vi.mock("./components/LTICallbackPage", () => ({
  default: () => <div data-testid="lti-callback-page">lti-callback-route</div>,
}));

function setAuthenticatedUser(role = "student") {
  mocks.session.authenticated = true;
  mocks.session.authReady = true;
  mocks.session.currentUser = { id: 7, email: "learner@example.com", role };
}

beforeEach(() => {
  vi.clearAllMocks();
  mocks.session.authenticated = false;
  mocks.session.authReady = true;
  mocks.session.currentUser = null;
  mocks.sessionExpired = null;
  mocks.incomingNotification = null;
  mocks.notificationsEnabled = null;
  mocks.socketEnabled = null;
  mocks.notifications.notifications = [];
  window.history.replaceState({}, "", "/");
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  window.history.replaceState({}, "", "/");
});

describe("App integration", () => {
  it("waits for session bootstrap before rendering authentication or learning UI", () => {
    mocks.session.authReady = false;

    render(<App />);

    expect(screen.getByText("...")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "fake-authenticate" })).not.toBeInTheDocument();
    expect(screen.queryByTestId("app-header")).not.toBeInTheDocument();
  });

  it("calls markAuthenticated and displays a success toast after authentication", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: "fake-authenticate" }));

    expect(mocks.session.markAuthenticated).toHaveBeenCalledTimes(1);
    expect(await screen.findByRole("status")).toHaveTextContent("تم تسجيل الدخول بنجاح");
    expect(screen.getByRole("status")).toHaveAttribute("data-toast-type", "success");
  });

  it("enables notification state and socket only for an authenticated session", () => {
    render(<App />);
    expect(mocks.notificationsEnabled).toBe(false);
    expect(mocks.socketEnabled).toBe(false);

    cleanup();
    setAuthenticatedUser("student");
    render(<App />);

    expect(mocks.notificationsEnabled).toBe(true);
    expect(mocks.socketEnabled).toBe(true);
    expect(screen.getByTestId("app-header")).toHaveAttribute("data-is-admin", "false");
    expect(screen.getByTestId("app-header")).toHaveAttribute("data-is-teacher", "false");
  });

  it.each([
    ["teacher", "false", "true"],
    ["admin", "true", "true"],
  ])("passes the correct role flags to the header for %s", (role, isAdmin, isTeacher) => {
    setAuthenticatedUser(role);
    render(<App />);

    expect(screen.getByTestId("app-header")).toHaveAttribute("data-is-admin", isAdmin);
    expect(screen.getByTestId("app-header")).toHaveAttribute("data-is-teacher", isTeacher);
  });

  it("opens a topic and moves from the topic panel to topic-specific content management", async () => {
    setAuthenticatedUser("teacher");
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: "select-topic" }));
    const topicPanel = await screen.findByTestId("topic-panel");
    expect(topicPanel).toHaveAttribute("data-topic-id", "42");
    expect(topicPanel).toHaveAttribute("data-is-teacher", "true");

    await user.click(screen.getByRole("button", { name: "manage-topic-content" }));

    expect(screen.queryByTestId("topic-panel")).not.toBeInTheDocument();
    const contentManager = await screen.findByTestId("content-manager");
    expect(contentManager).toHaveAttribute("data-topic-id", "42");
  });

  it("opens the global content manager from the header without a selected topic", async () => {
    setAuthenticatedUser("teacher");
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: "open-content" }));

    expect(await screen.findByTestId("content-manager")).toHaveAttribute("data-topic-id", "all");
  });

  it("closes session-bound panels immediately on logout", async () => {
    setAuthenticatedUser("student");
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: "open-files" }));
    expect(await screen.findByTestId("files-panel")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "open-account" }));
    expect(await screen.findByTestId("account-settings")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "logout" }));

    expect(mocks.session.logout).toHaveBeenCalledTimes(1);
    await waitFor(() => {
      expect(screen.queryByTestId("files-panel")).not.toBeInTheDocument();
      expect(screen.queryByTestId("account-settings")).not.toBeInTheDocument();
    });
  });

  it("clears session panels and notifies the user when the session expires", async () => {
    setAuthenticatedUser("student");
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: "open-files" }));
    expect(await screen.findByTestId("files-panel")).toBeInTheDocument();

    act(() => {
      mocks.sessionExpired();
    });

    expect(screen.queryByTestId("files-panel")).not.toBeInTheDocument();
    expect(await screen.findByRole("status")).toHaveTextContent(
      "انتهت الجلسة، سجّل الدخول مرة أخرى"
    );
    expect(screen.getByRole("status")).toHaveAttribute("data-toast-type", "error");
  });

  it("adds incoming notifications and displays their title", () => {
    setAuthenticatedUser("student");
    render(<App />);
    const notification = { id: 9, title: "تم نشر درس جديد" };

    act(() => {
      mocks.incomingNotification(notification);
    });

    expect(mocks.notifications.addNotification).toHaveBeenCalledWith(notification);
    expect(screen.getByRole("status")).toHaveTextContent("تم نشر درس جديد");
  });

  it("changes the application language from the header callback", async () => {
    setAuthenticatedUser("student");
    const changeLanguage = vi
      .spyOn(i18n, "changeLanguage")
      .mockResolvedValue(i18n.t.bind(i18n));
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: "switch-language" }));

    expect(changeLanguage).toHaveBeenCalledWith("en");
  });

  it("closes all supported modal components through their close callbacks", async () => {
    setAuthenticatedUser("admin");
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: "open-admin" }));
    expect(await screen.findByTestId("admin-dashboard")).toHaveAttribute("data-user-id", "7");
    await user.click(screen.getByRole("button", { name: "close-admin" }));
    await waitFor(() => expect(screen.queryByTestId("admin-dashboard")).not.toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: "open-billing" }));
    expect(await screen.findByTestId("billing-panel")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "close-billing" }));
    await waitFor(() => expect(screen.queryByTestId("billing-panel")).not.toBeInTheDocument());
  });

  it("renders the verification page for its dedicated route", async () => {
    window.history.replaceState({}, "", "/verify-email");

    render(<App />);

    expect(await screen.findByTestId("verify-email-page")).toBeInTheDocument();
    expect(screen.queryByTestId("app-header")).not.toBeInTheDocument();
  });
});
