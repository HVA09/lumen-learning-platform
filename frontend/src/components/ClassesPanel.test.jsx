import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../lib/classesApi", () => ({
  listClasses: vi.fn(),
  createClass: vi.fn(),
  getClassDetail: vi.fn(),
  joinClass: vi.fn(),
  renameClass: vi.fn(),
  regenerateInviteCode: vi.fn(),
  deleteClass: vi.fn(),
  removeStudentFromClass: vi.fn(),
}));

import {
  createClass,
  deleteClass,
  getClassDetail,
  joinClass,
  listClasses,
  regenerateInviteCode,
  removeStudentFromClass,
} from "../lib/classesApi";
import ClassesPanel from "./ClassesPanel";

const myClass = { id: 7, name: "رياضيات — الصف العاشر", invite_code: "K7M2PQ", teacher_user_id: 2, is_archived: false, created_at: "2026-09-29T00:00:00Z", student_count: 1 };
const detail = {
  ...myClass,
  students: [{ user_id: 41, email: "s41@example.com", display_name: "سعد", joined_at: "2026-09-29T00:00:00Z", average_mastery: 62.5 }],
};

beforeEach(() => {
  vi.clearAllMocks();
  listClasses.mockResolvedValue([]);
});

describe("ClassesPanel — الطالب", () => {
  it("ينضم برمز الدعوة ويظهر الفصل بعدها", async () => {
    joinClass.mockResolvedValue(myClass);
    listClasses.mockResolvedValueOnce([]).mockResolvedValue([myClass]);
    const user = userEvent.setup();
    render(<ClassesPanel isTeacher={false} onClose={vi.fn()} />);

    expect(await screen.findByText("ما انضممت لأي فصل بعد — اطلب الرمز من معلّمك")).toBeInTheDocument();
    await user.type(screen.getByPlaceholderText("رمز الانضمام من معلّمك"), "k7m2pq");
    await user.click(screen.getByRole("button", { name: "انضمام" }));

    expect(joinClass).toHaveBeenCalledWith("k7m2pq");
    expect(await screen.findByText("انضممت إلى فصل «رياضيات — الصف العاشر»")).toBeInTheDocument();
    expect(await screen.findByText("1 طالب")).toBeInTheDocument();
  });

  it("رمز غلط يعرض رسالة السيرفر", async () => {
    joinClass.mockRejectedValue({ response: { data: { detail: "رمز الدعوة غير صحيح" } } });
    const user = userEvent.setup();
    render(<ClassesPanel isTeacher={false} onClose={vi.fn()} />);
    await user.type(await screen.findByPlaceholderText("رمز الانضمام من معلّمك"), "BAD");
    await user.click(screen.getByRole("button", { name: "انضمام" }));
    expect(await screen.findByText("رمز الدعوة غير صحيح")).toBeInTheDocument();
  });

  it("زر الانضمام معطّل لين يكتب رمزًا، والطالب لا يرى رمز الفصل ولا الإدارة", async () => {
    listClasses.mockResolvedValue([myClass]);
    render(<ClassesPanel isTeacher={false} onClose={vi.fn()} />);
    expect(await screen.findByText("رياضيات — الصف العاشر")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "انضمام" })).toBeDisabled();
    expect(screen.queryByText("K7M2PQ")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "إدارة" })).not.toBeInTheDocument();
  });
});

describe("ClassesPanel — المعلّم", () => {
  it("ينشئ فصلًا باسم منظّف من المسافات", async () => {
    createClass.mockResolvedValue(myClass);
    listClasses.mockResolvedValueOnce([]).mockResolvedValue([myClass]);
    const user = userEvent.setup();
    render(<ClassesPanel isTeacher onClose={vi.fn()} />);

    await user.type(await screen.findByPlaceholderText(/اسم الفصل الجديد/), "  رياضيات — الصف العاشر  ");
    await user.click(screen.getByRole("button", { name: "إنشاء" }));

    expect(createClass).toHaveBeenCalledWith("رياضيات — الصف العاشر");
    expect(await screen.findByText("K7M2PQ")).toBeInTheDocument();
  });

  it("إدارة الفصل: القائمة ومتوسط الإتقان، تجديد الرمز بعد التأكيد، وإزالة طالب", async () => {
    listClasses.mockResolvedValue([myClass]);
    getClassDetail.mockResolvedValue(detail);
    regenerateInviteCode.mockResolvedValue({ ...myClass, invite_code: "ZZ9988" });
    removeStudentFromClass.mockResolvedValue();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const user = userEvent.setup();
    render(<ClassesPanel isTeacher onClose={vi.fn()} />);

    await user.click(await screen.findByRole("button", { name: "إدارة" }));
    expect(await screen.findByText("الطلاب (1)")).toBeInTheDocument();
    expect(screen.getByText("سعد")).toBeInTheDocument();
    expect(screen.getByText("63%")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "تجديد الرمز" }));
    expect(regenerateInviteCode).toHaveBeenCalledWith(7);

    await user.click(screen.getByRole("button", { name: "إزالة" }));
    expect(removeStudentFromClass).toHaveBeenCalledWith(7, 41);
  });

  it("لا يجدّد الرمز لو المعلّم رفض التأكيد", async () => {
    listClasses.mockResolvedValue([myClass]);
    getClassDetail.mockResolvedValue(detail);
    vi.spyOn(window, "confirm").mockReturnValue(false);
    const user = userEvent.setup();
    render(<ClassesPanel isTeacher onClose={vi.fn()} />);
    await user.click(await screen.findByRole("button", { name: "إدارة" }));
    await user.click(await screen.findByRole("button", { name: "تجديد الرمز" }));
    expect(regenerateInviteCode).not.toHaveBeenCalled();
  });

  it("حذف الفصل يرجع للقائمة بدون محاولة جلب الفصل المحذوف", async () => {
    listClasses.mockResolvedValueOnce([myClass]).mockResolvedValue([]);
    getClassDetail.mockResolvedValue(detail);
    deleteClass.mockResolvedValue();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const user = userEvent.setup();
    render(<ClassesPanel isTeacher onClose={vi.fn()} />);

    await user.click(await screen.findByRole("button", { name: "إدارة" }));
    await user.click(await screen.findByRole("button", { name: "حذف الفصل" }));

    expect(deleteClass).toHaveBeenCalledWith(7);
    expect(await screen.findByText("ما أنشأت فصولًا بعد")).toBeInTheDocument();
    expect(getClassDetail).toHaveBeenCalledTimes(1); // مرة وحدة عند فتح الإدارة فقط
  });
});
