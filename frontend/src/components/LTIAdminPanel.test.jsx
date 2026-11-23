import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const ltiApi = vi.hoisted(() => ({
  listLtiPlatforms: vi.fn(),
  createLtiPlatform: vi.fn(),
  listLtiResourceLinks: vi.fn(),
  listLtiAssignmentLinks: vi.fn(),
  createLtiAssignmentLink: vi.fn(),
  listLtiGradeEvents: vi.fn(),
  retryLtiGradeEvent: vi.fn(),
}));
const assignmentsApi = vi.hoisted(() => ({ getAssignments: vi.fn() }));

vi.mock("../lib/ltiApi", () => ltiApi);
vi.mock("../lib/assignmentsApi", () => assignmentsApi);

import LTIAdminPanel from "./LTIAdminPanel";

const platform = {
  id: 4,
  name: "Moodle التجريبي",
  issuer: "https://moodle.example.test",
  client_id: "client-4",
  deployment_id: "deployment-4",
};
const resource = {
  id: 9,
  platform_id: 4,
  deployment_id: "deployment-4",
  resource_link_id: "course-resource-9",
  lineitem_ready: true,
  score_scope_allowed: true,
  mapped_assignment_id: null,
};
const assignment = { id: 12, title: "مقدمة البرمجة" };
const event = {
  id: 21,
  submission_id: 33,
  grade_version: 2,
  status: "dead",
  score_timestamp: "2026-11-22T12:00:00Z",
  attempts: 8,
  last_error: "Timeout: AGS delivery failed",
  created_at: "2026-11-22T11:00:00Z",
  delivered_at: null,
};

beforeEach(() => {
  vi.clearAllMocks();
  ltiApi.listLtiPlatforms.mockResolvedValue([platform]);
  ltiApi.listLtiResourceLinks.mockResolvedValue([resource]);
  ltiApi.listLtiAssignmentLinks.mockResolvedValue([]);
  ltiApi.listLtiGradeEvents.mockResolvedValue([event]);
  ltiApi.createLtiPlatform.mockResolvedValue(platform);
  ltiApi.createLtiAssignmentLink.mockResolvedValue({ id: 10 });
  ltiApi.retryLtiGradeEvent.mockResolvedValue({ ...event, status: "pending" });
  assignmentsApi.getAssignments.mockResolvedValue([assignment]);
});

describe("LTIAdminPanel", () => {
  it("loads platform, resource, and grade-event operational data", async () => {
    render(<LTIAdminPanel />);

    expect(await screen.findByText("Moodle التجريبي")).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /course-resource-9/ })).toBeInTheDocument();
    expect(screen.getByText(/حدث #21/)).toBeInTheDocument();
    expect(screen.getByText(/آخر خطأ: Timeout: AGS delivery failed/)).toBeInTheDocument();
  });

  it("registers a platform through the admin API", async () => {
    const user = userEvent.setup();
    render(<LTIAdminPanel />);

    await screen.findByText("Moodle التجريبي");
    await user.type(screen.getByLabelText("اسم المنصة"), "Canvas تجريبي");
    await user.type(screen.getByLabelText("Issuer URL"), "https://canvas.example.test");
    await user.type(screen.getByLabelText("Client ID"), "canvas-client");
    await user.type(screen.getByLabelText("Deployment ID"), "canvas-deployment");
    await user.type(screen.getByLabelText("OIDC Login URL"), "https://canvas.example.test/login");
    await user.type(screen.getByLabelText("OAuth Token URL"), "https://canvas.example.test/token");
    await user.type(screen.getByLabelText("JWKS URL"), "https://canvas.example.test/jwks");
    await user.click(screen.getByRole("button", { name: "تسجيل المنصة" }));

    await waitFor(() => {
      expect(ltiApi.createLtiPlatform).toHaveBeenCalledWith({
        name: "Canvas تجريبي",
        issuer: "https://canvas.example.test",
        client_id: "canvas-client",
        deployment_id: "canvas-deployment",
        auth_login_url: "https://canvas.example.test/login",
        auth_token_url: "https://canvas.example.test/token",
        jwks_url: "https://canvas.example.test/jwks",
      });
    });
  });

  it("maps only a discovered score-ready resource to a Lumen assignment", async () => {
    const user = userEvent.setup();
    render(<LTIAdminPanel />);

    await screen.findByRole("option", { name: /course-resource-9/ });
    await user.selectOptions(screen.getByLabelText("مورد المنصة"), "9");
    await user.selectOptions(screen.getByLabelText("واجب Lumen"), "12");
    await user.clear(screen.getByLabelText("الدرجة القصوى في منصة LMS"));
    await user.type(screen.getByLabelText("الدرجة القصوى في منصة LMS"), "50");
    await user.click(screen.getByRole("button", { name: "حفظ الربط" }));

    await waitFor(() => {
      expect(ltiApi.createLtiAssignmentLink).toHaveBeenCalledWith({
        platform_id: 4,
        assignment_id: 12,
        resource_link_id: "course-resource-9",
        score_maximum: 50,
      });
    });
  });

  it("authorizes one retry for a dead grade event", async () => {
    const user = userEvent.setup();
    render(<LTIAdminPanel />);

    await screen.findByText(/حدث #21/);
    await user.click(screen.getByRole("button", { name: "تفويض إعادة محاولة واحدة" }));

    await waitFor(() => expect(ltiApi.retryLtiGradeEvent).toHaveBeenCalledWith(21));
    expect(await screen.findByRole("status")).toHaveTextContent("تم تفويض محاولة إعادة الإرسال مرة واحدة");
  });

  it("shows an actionable error when LTI data cannot be loaded", async () => {
    ltiApi.listLtiPlatforms.mockRejectedValueOnce({
      response: { data: { detail: "LTI API unavailable" } },
    });
    render(<LTIAdminPanel />);

    expect(await screen.findByRole("alert")).toHaveTextContent("LTI API unavailable");
  });
});
