import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../lib/assignmentsApi", () => ({
  getAssignments: vi.fn(),
  createAssignment: vi.fn(),
  deleteAssignment: vi.fn(),
  getMySubmission: vi.fn(),
  gradeSubmission: vi.fn(),
  listSubmissions: vi.fn(),
  submitAssignment: vi.fn(),
}));
vi.mock("../lib/classesApi", () => ({ listClasses: vi.fn() }));

import { createAssignment, getAssignments } from "../lib/assignmentsApi";
import { listClasses } from "../lib/classesApi";
import AssignmentsPanel from "./AssignmentsPanel";

const classes = [{ id: 7, name: "فصل التجربة", invite_code: "AAAAAA", student_count: 3 }];
const classAssignment = {
  id: 1, created_by_user_id: 5, topic_id: null, class_section_id: 7, title: "واجب المشتقات",
  description: "احسب $f'(x)$", rubric_criteria: [], due_at: null, created_at: "2026-09-29T00:00:00Z",
  can_manage: true, my_status: null, my_grade_percentage: null, submissions_count: 2, pending_grading_count: 1,
};

beforeEach(() => {
  vi.clearAllMocks();
  listClasses.mockResolvedValue(classes);
  getAssignments.mockResolvedValue([]);
});

describe("AssignmentsPanel", () => {
  it("المعلّم يوجّه الواجب لفصل فيُرسل class_section_id رقميًا", async () => {
    createAssignment.mockResolvedValue(classAssignment);
    const user = userEvent.setup();
    render(<AssignmentsPanel isTeacher onClose={vi.fn()} />);

    await user.click(await screen.findByText("+ واجب جديد"));
    await user.type(screen.getByPlaceholderText("عنوان الواجب"), "واجب المشتقات");
    await user.type(screen.getByPlaceholderText(/وصف الواجب/), "اشتق الدالة");
    await user.selectOptions(screen.getAllByRole("combobox")[0], "7");
    await user.click(screen.getByRole("button", { name: "إنشاء الواجب" }));

    expect(createAssignment).toHaveBeenCalledWith(
      expect.objectContaining({ title: "واجب المشتقات", description: "اشتق الدالة", class_section_id: 7 })
    );
  });

  it("بدون اختيار فصل يُرسل null (واجب عام)", async () => {
    createAssignment.mockResolvedValue({ ...classAssignment, class_section_id: null });
    const user = userEvent.setup();
    render(<AssignmentsPanel isTeacher onClose={vi.fn()} />);
    await user.click(await screen.findByText("+ واجب جديد"));
    await user.type(screen.getByPlaceholderText("عنوان الواجب"), "عام");
    await user.type(screen.getByPlaceholderText(/وصف الواجب/), "وصف");
    await user.click(screen.getByRole("button", { name: "إنشاء الواجب" }));
    expect(createAssignment).toHaveBeenCalledWith(expect.objectContaining({ class_section_id: null }));
  });

  it("القائمة تعرض شارة اسم الفصل وأعداد التسليمات للمعلّم", async () => {
    getAssignments.mockResolvedValue([classAssignment]);
    render(<AssignmentsPanel isTeacher onClose={vi.fn()} />);
    expect(await screen.findByText("واجب المشتقات")).toBeInTheDocument();
    expect(screen.getByText("فصل التجربة")).toBeInTheDocument();
    expect(screen.getByText("2 تسليم · 1 بانتظار التقييم")).toBeInTheDocument();
  });

  it("الطالب لا يرى زر إنشاء واجب", async () => {
    render(<AssignmentsPanel isTeacher={false} onClose={vi.fn()} />);
    expect(await screen.findByText("ما فيه واجبات حاليًا")).toBeInTheDocument();
    expect(screen.queryByText("+ واجب جديد")).not.toBeInTheDocument();
  });
});


  it("المعلّم لا يرى أدوات التقييم أو الحذف للواجب العام الذي لا يملكه", async () => {
    getAssignments.mockResolvedValue([{ ...classAssignment, class_section_id: null, can_manage: false }]);
    const { getMySubmission } = await import("../lib/assignmentsApi");
    getMySubmission.mockResolvedValue(null);
    const user = userEvent.setup();
    render(<AssignmentsPanel isTeacher onClose={vi.fn()} />);

    await user.click(await screen.findByText("واجب المشتقات"));
    expect(await screen.findByPlaceholderText("اكتب إجابتك وشرحك هنا...")).toBeInTheDocument();
    expect(screen.queryByText("قيّم الآن")).not.toBeInTheDocument();
    expect(screen.queryByText("حذف الواجب")).not.toBeInTheDocument();
  });
