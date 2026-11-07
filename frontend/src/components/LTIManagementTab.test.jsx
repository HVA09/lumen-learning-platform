import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

vi.mock("../lib/assignmentsApi", () => ({
  getAssignments: vi.fn(),
}));

vi.mock("../lib/ltiApi", () => ({
  listLtiPlatforms: vi.fn(),
  registerLtiPlatform: vi.fn(),
  listDiscoveredResourceLinks: vi.fn(),
  listLtiAssignmentLinks: vi.fn(),
  createLtiAssignmentLink: vi.fn(),
  listLtiGradeEvents: vi.fn(),
  retryLtiGradeEvent: vi.fn(),
}));

import { getAssignments } from "../lib/assignmentsApi";
import {
  createLtiAssignmentLink,
  listDiscoveredResourceLinks,
  listLtiAssignmentLinks,
  listLtiGradeEvents,
  listLtiPlatforms,
  registerLtiPlatform,
  retryLtiGradeEvent,
} from "../lib/ltiApi";
import LTIManagementTab from "./LTIManagementTab";

const assignments = [{ id: 17, title: "واجب الكسور" }];
const platforms = [{
  id: 2,
  name: "Moodle Sandbox",
  issuer: "https://moodle.example.test",
  client_id: "client-1",
  deployment_id: "deployment-1",
}];

function mockDashboardData({ resources = [], mappings = [], events = [] } = {}) {
  getAssignments.mockResolvedValue(assignments);
  listLtiPlatforms.mockResolvedValue(platforms);
  listDiscoveredResourceLinks.mockResolvedValue(resources);
  listLtiAssignmentLinks.mockResolvedValue(mappings);
  listLtiGradeEvents.mockResolvedValue(events);
}

beforeEach(() => {
  vi.clearAllMocks();
  mockDashboardData();
  registerLtiPlatform.mockResolvedValue({ id: 2 });
  createLtiAssignmentLink.mockResolvedValue({ id: 9 });
  retryLtiGradeEvent.mockResolvedValue({ id: 4, status: "pending" });
});

describe("LTIManagementTab", () => {
  it("يسجل منصة باستخدام بيانات LMS الرسمية", async () => {
    render(<LTIManagementTab />);
    await screen.findByText("Moodle Sandbox");

    fireEvent.change(screen.getByLabelText("اسم المنصة"), { target: { value: "Canvas Test" } });
    fireEvent.change(screen.getByLabelText("Issuer"), { target: { value: "https://canvas.example.test" } });
    fireEvent.change(screen.getByLabelText("Client ID"), { target: { value: "canvas-client" } });
    fireEvent.change(screen.getByLabelText("Deployment ID"), { target: { value: "canvas-deploy" } });
    fireEvent.change(screen.getByLabelText("OIDC Authorization URL"), { target: { value: "https://canvas.example.test/login" } });
    fireEvent.change(screen.getByLabelText("OAuth Token URL"), { target: { value: "https://canvas.example.test/token" } });
    fireEvent.change(screen.getByLabelText("Platform JWKS URL"), { target: { value: "https://canvas.example.test/jwks" } });
    fireEvent.click(screen.getByRole("button", { name: "تسجيل المنصة" }));

    await waitFor(() => {
      expect(registerLtiPlatform).toHaveBeenCalledWith(expect.objectContaining({
        name: "Canvas Test",
        issuer: "https://canvas.example.test",
        client_id: "canvas-client",
        deployment_id: "canvas-deploy",
      }));
    });
  });

  it("يربط المورد المكتشف بواجب ويحدد الدرجة القصوى", async () => {
    mockDashboardData({
      resources: [{
        id: 5,
        platform_id: 2,
        deployment_id: "deployment-1",
        resource_link_id: "resource-123",
        lineitem_ready: true,
        score_scope_allowed: true,
        mapped_assignment_id: null,
        first_seen_at: "2026-11-01T10:00:00Z",
        last_seen_at: "2026-11-02T10:00:00Z",
      }],
    });
    render(<LTIManagementTab />);

    await screen.findByText("resource-123");
    fireEvent.change(screen.getByLabelText("الدرجة القصوى للمورد resource-123"), {
      target: { value: "25" },
    });
    fireEvent.click(screen.getByRole("button", { name: "ربط الواجب" }));

    await waitFor(() => {
      expect(createLtiAssignmentLink).toHaveBeenCalledWith({
        platform_id: 2,
        assignment_id: 17,
        resource_link_id: "resource-123",
        score_maximum: 25,
      });
    });
  });

  it("يتيح إعادة محاولة الحدث المتوقف ويحدّث السجل", async () => {
    mockDashboardData({
      events: [{
        id: 4,
        submission_id: 12,
        grade_version: 2,
        status: "dead",
        attempts: 8,
        last_error: "ValueError: AGS delivery failed",
        created_at: "2026-11-02T10:00:00Z",
        delivered_at: null,
      }],
    });
    render(<LTIManagementTab />);

    fireEvent.click(await screen.findByRole("button", { name: "إعادة المحاولة" }));

    await waitFor(() => {
      expect(retryLtiGradeEvent).toHaveBeenCalledWith(4);
      expect(listLtiGradeEvents).toHaveBeenCalledTimes(2);
    });
  });
});
