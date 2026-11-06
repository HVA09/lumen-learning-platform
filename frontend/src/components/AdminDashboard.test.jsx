import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const adminApi = vi.hoisted(() => ({
  getAdminStats: vi.fn(),
  getDailyAnalytics: vi.fn(),
  downloadAnalyticsCsv: vi.fn(),
  listAllUsers: vi.fn(),
  updateUser: vi.fn(),
  deleteUser: vi.fn(),
  listAuditLogs: vi.fn(),
}));

vi.mock("../lib/adminApi", () => adminApi);
vi.mock("recharts", () => ({
  CartesianGrid: () => null,
  Line: () => null,
  LineChart: () => null,
  ResponsiveContainer: () => null,
  Tooltip: () => null,
  XAxis: () => null,
  YAxis: () => null,
}));

import AdminDashboard from "./AdminDashboard";

const currentAdmin = {
  id: 1,
  email: "admin@example.com",
  role: "admin",
  is_active: true,
  is_email_verified: true,
};

const student = {
  id: 2,
  email: "student@example.com",
  role: "user",
  is_active: true,
  is_email_verified: false,
};

const stats = {
  total_students: 8,
  total_teachers: 3,
  total_lessons: 24,
  total_questions: 60,
  total_quiz_attempts: 95,
  total_assignments: 6,
  total_submissions: 12,
  storage_used_bytes: 2048,
};

beforeEach(() => {
  vi.clearAllMocks();
  adminApi.getAdminStats.mockResolvedValue(stats);
  adminApi.getDailyAnalytics.mockResolvedValue([
    {
      date: "2026-11-05",
      new_users: 2,
      quiz_attempts: 5,
      average_quiz_score: 80,
      assignment_submissions: 1,
    },
  ]);
  adminApi.downloadAnalyticsCsv.mockResolvedValue(undefined);
  adminApi.listAllUsers.mockResolvedValue([currentAdmin, student]);
  adminApi.updateUser.mockResolvedValue(student);
  adminApi.deleteUser.mockResolvedValue(undefined);
  adminApi.listAuditLogs.mockResolvedValue([]);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("AdminDashboard", () => {
  it("loads administration statistics and formats storage usage", async () => {
    render(<AdminDashboard currentUserId={currentAdmin.id} onClose={vi.fn()} />);

    expect(await screen.findByText("8")).toBeInTheDocument();
    expect(screen.getByText("الطلاب")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("المعلّمون")).toBeInTheDocument();
    expect(screen.getByText("2.0 KB")).toBeInTheDocument();
    expect(adminApi.getDailyAnalytics).toHaveBeenCalledWith(30);
  });

  it("exports the default thirty-day analytics period", async () => {
    const user = userEvent.setup();
    render(<AdminDashboard currentUserId={currentAdmin.id} onClose={vi.fn()} />);

    await user.click(await screen.findByRole("button", { name: "تصدير CSV" }));
    expect(adminApi.downloadAnalyticsCsv).toHaveBeenCalledWith(30);
  });

  it("shows an error when administration statistics cannot be loaded", async () => {
    adminApi.getAdminStats.mockRejectedValueOnce(new Error("request failed"));
    render(<AdminDashboard currentUserId={currentAdmin.id} onClose={vi.fn()} />);

    expect(await screen.findByText("تعذر تحميل الإحصائيات")).toBeInTheDocument();
  });

  it("prevents the current administrator from changing or deleting their own account", async () => {
    const user = userEvent.setup();
    render(<AdminDashboard currentUserId={currentAdmin.id} onClose={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "المستخدمون" }));

    const currentRow = (await screen.findByText(currentAdmin.email)).parentElement.parentElement;
    expect(within(currentRow).getByRole("combobox")).toBeDisabled();
    expect(within(currentRow).getByRole("button", { name: "تعطيل" })).toBeDisabled();
    expect(within(currentRow).queryByRole("button", { name: "حذف" })).not.toBeInTheDocument();
    expect(adminApi.updateUser).not.toHaveBeenCalled();
    expect(adminApi.deleteUser).not.toHaveBeenCalled();
  });

  it("updates another user's role with the selected value", async () => {
    const user = userEvent.setup();
    render(<AdminDashboard currentUserId={currentAdmin.id} onClose={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "المستخدمون" }));

    await screen.findByText(student.email);
    const studentRow = screen.getByText(student.email).parentElement.parentElement;
    await user.selectOptions(within(studentRow).getByRole("combobox"), "teacher");

    await waitFor(() => {
      expect(adminApi.updateUser).toHaveBeenCalledWith(student.id, { role: "teacher" });
    });
  });

  it("toggles another user's active state and deletes only after confirmation", async () => {
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    const user = userEvent.setup();
    render(<AdminDashboard currentUserId={currentAdmin.id} onClose={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "المستخدمون" }));

    await screen.findByText(student.email);
    const studentRow = screen.getByText(student.email).parentElement.parentElement;
    await user.click(within(studentRow).getByRole("button", { name: "تعطيل" }));
    expect(adminApi.updateUser).toHaveBeenCalledWith(student.id, { is_active: false });

    await screen.findByText(student.email);
    const refreshedStudentRow = screen.getByText(student.email).parentElement.parentElement;
    await user.click(within(refreshedStudentRow).getByRole("button", { name: "حذف" }));
    expect(confirm).toHaveBeenCalledWith(`حذف المستخدم ${student.email}؟`);
    expect(adminApi.deleteUser).toHaveBeenCalledWith(student.id);
  });

  it("shows the server error when a user update is rejected", async () => {
    adminApi.updateUser.mockRejectedValueOnce({
      response: { data: { detail: "لا يمكن تنفيذ هذا التغيير" } },
    });
    const user = userEvent.setup();
    render(<AdminDashboard currentUserId={currentAdmin.id} onClose={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "المستخدمون" }));

    await screen.findByText(student.email);
    const studentRow = screen.getByText(student.email).parentElement.parentElement;
    await user.selectOptions(within(studentRow).getByRole("combobox"), "teacher");

    expect(await screen.findByText("لا يمكن تنفيذ هذا التغيير")).toBeInTheDocument();
  });

  it("displays audit events in the logs tab", async () => {
    adminApi.listAuditLogs.mockResolvedValueOnce([
      {
        id: 9,
        event_type: "user.login",
        created_at: "2026-11-06T10:00:00Z",
        description: "تم تسجيل دخول المستخدم",
      },
    ]);
    const user = userEvent.setup();
    render(<AdminDashboard currentUserId={currentAdmin.id} onClose={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "السجل" }));

    expect(await screen.findByText("user.login")).toBeInTheDocument();
    expect(screen.getByText("تم تسجيل دخول المستخدم")).toBeInTheDocument();
  });

  it("shows an empty state when there are no audit events", async () => {
    const user = userEvent.setup();
    render(<AdminDashboard currentUserId={currentAdmin.id} onClose={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "السجل" }));

    expect(await screen.findByText("لا توجد أحداث بعد")).toBeInTheDocument();
  });

  it("calls onClose when the dashboard is closed", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<AdminDashboard currentUserId={currentAdmin.id} onClose={onClose} />);

    await user.click(screen.getByRole("button", { name: "✕" }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
