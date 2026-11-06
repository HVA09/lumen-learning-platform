import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const filesApi = vi.hoisted(() => ({
  deleteFile: vi.fn(),
  downloadFile: vi.fn(),
  fetchFileBlob: vi.fn(),
  listFiles: vi.fn(),
  uploadFile: vi.fn(),
}));

vi.mock("../lib/filesApi", () => filesApi);

import FilesPanel from "./FilesPanel";

const imageFile = {
  id: 11,
  original_filename: "diagram.png",
  content_type: "image/png",
  size_bytes: 2048,
};

const textFile = {
  id: 12,
  original_filename: "notes.txt",
  content_type: "text/plain",
  size_bytes: 512,
};

let originalCreateObjectURL;
let originalRevokeObjectURL;

beforeEach(() => {
  vi.clearAllMocks();
  filesApi.deleteFile.mockResolvedValue(undefined);
  filesApi.downloadFile.mockResolvedValue(undefined);
  filesApi.fetchFileBlob.mockResolvedValue(new Blob(["preview"]));
  filesApi.listFiles.mockResolvedValue([]);
  filesApi.uploadFile.mockResolvedValue({ id: 13 });
  originalCreateObjectURL = Object.getOwnPropertyDescriptor(window.URL, "createObjectURL");
  originalRevokeObjectURL = Object.getOwnPropertyDescriptor(window.URL, "revokeObjectURL");
});

afterEach(() => {
  vi.restoreAllMocks();
  if (originalCreateObjectURL) {
    Object.defineProperty(window.URL, "createObjectURL", originalCreateObjectURL);
  } else {
    delete window.URL.createObjectURL;
  }
  if (originalRevokeObjectURL) {
    Object.defineProperty(window.URL, "revokeObjectURL", originalRevokeObjectURL);
  } else {
    delete window.URL.revokeObjectURL;
  }
});

describe("FilesPanel", () => {
  it("loads and displays file names and formatted sizes", async () => {
    filesApi.listFiles.mockResolvedValueOnce([imageFile, textFile]);
    render(<FilesPanel onClose={vi.fn()} />);

    expect(await screen.findByText("diagram.png")).toBeInTheDocument();
    expect(screen.getByText("2.0 KB")).toBeInTheDocument();
    expect(screen.getByText("notes.txt")).toBeInTheDocument();
    expect(screen.getByText("512 B")).toBeInTheDocument();
  });

  it("shows a load error when the file list request fails", async () => {
    filesApi.listFiles.mockRejectedValueOnce(new Error("network unavailable"));
    render(<FilesPanel onClose={vi.fn()} />);

    expect(await screen.findByText("تعذر تحميل قائمة الملفات")).toBeInTheDocument();
  });

  it("uploads a selected file, reports progress, and refreshes the list", async () => {
    const uploadedFile = { ...textFile, id: 13, original_filename: "report.pdf" };
    const selectedFile = new File(["report"], "report.pdf", { type: "application/pdf" });
    let finishUpload;
    filesApi.listFiles
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([uploadedFile]);
    filesApi.uploadFile.mockImplementation((_file, onProgress) => {
      onProgress(60);
      return new Promise((resolve) => {
        finishUpload = resolve;
      });
    });

    const { container } = render(<FilesPanel onClose={vi.fn()} />);
    expect(await screen.findByText("لا توجد ملفات بعد")).toBeInTheDocument();

    fireEvent.change(container.querySelector('input[type="file"]'), {
      target: { files: [selectedFile] },
    });

    expect(filesApi.uploadFile).toHaveBeenCalledWith(selectedFile, expect.any(Function));
    expect(await screen.findByText("60%")).toBeInTheDocument();

    await act(async () => {
      finishUpload({ id: 13 });
    });

    expect(await screen.findByText("report.pdf")).toBeInTheDocument();
    expect(filesApi.listFiles).toHaveBeenCalledTimes(2);
  });

  it("shows the server upload error and clears progress after failure", async () => {
    const selectedFile = new File(["bad"], "bad.exe", { type: "application/octet-stream" });
    filesApi.uploadFile.mockRejectedValueOnce({
      response: { data: { detail: "نوع الملف غير مسموح" } },
    });
    const { container } = render(<FilesPanel onClose={vi.fn()} />);
    await screen.findByText("لا توجد ملفات بعد");

    fireEvent.change(container.querySelector('input[type="file"]'), {
      target: { files: [selectedFile] },
    });

    expect(await screen.findByText("نوع الملف غير مسموح")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText("0%")).not.toBeInTheDocument());
  });

  it("deletes a file after confirmation and removes it from the list", async () => {
    filesApi.listFiles.mockResolvedValueOnce([textFile]);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const user = userEvent.setup();
    render(<FilesPanel onClose={vi.fn()} />);

    expect(await screen.findByText("notes.txt")).toBeInTheDocument();
    await user.click(screen.getByTitle("حذف"));

    expect(window.confirm).toHaveBeenCalledWith("حذف هذا الملف؟");
    expect(filesApi.deleteFile).toHaveBeenCalledWith(textFile.id);
    await waitFor(() => expect(screen.queryByText("notes.txt")).not.toBeInTheDocument());
  });

  it("does not delete a file when confirmation is cancelled", async () => {
    filesApi.listFiles.mockResolvedValueOnce([textFile]);
    vi.spyOn(window, "confirm").mockReturnValue(false);
    const user = userEvent.setup();
    render(<FilesPanel onClose={vi.fn()} />);

    expect(await screen.findByText("notes.txt")).toBeInTheDocument();
    await user.click(screen.getByTitle("حذف"));

    expect(filesApi.deleteFile).not.toHaveBeenCalled();
    expect(screen.getByText("notes.txt")).toBeInTheDocument();
  });

  it("shows an error and keeps the file when deletion fails", async () => {
    filesApi.listFiles.mockResolvedValueOnce([textFile]);
    filesApi.deleteFile.mockRejectedValueOnce(new Error("delete failed"));
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const user = userEvent.setup();
    render(<FilesPanel onClose={vi.fn()} />);

    await screen.findByText("notes.txt");
    await user.click(screen.getByTitle("حذف"));

    expect(await screen.findByText("تعذر حذف الملف")).toBeInTheDocument();
    expect(screen.getByText("notes.txt")).toBeInTheDocument();
  });

  it("previews an image and revokes its object URL when closed", async () => {
    const createObjectURL = vi.fn(() => "blob:files-panel-preview");
    const revokeObjectURL = vi.fn();
    Object.defineProperty(window.URL, "createObjectURL", {
      configurable: true,
      value: createObjectURL,
    });
    Object.defineProperty(window.URL, "revokeObjectURL", {
      configurable: true,
      value: revokeObjectURL,
    });
    filesApi.listFiles.mockResolvedValueOnce([imageFile]);
    const user = userEvent.setup();
    render(<FilesPanel onClose={vi.fn()} />);

    await user.click(await screen.findByText("diagram.png"));
    const previewImage = await screen.findByRole("img", { name: "diagram.png" });
    expect(filesApi.fetchFileBlob).toHaveBeenCalledWith(imageFile.id);
    expect(previewImage).toHaveAttribute("src", "blob:files-panel-preview");

    await user.click(previewImage);
    await waitFor(() => {
      expect(revokeObjectURL).toHaveBeenCalledWith("blob:files-panel-preview");
    });
    expect(screen.queryByRole("img", { name: "diagram.png" })).not.toBeInTheDocument();
  });

  it("downloads a non-previewable file when its name is selected", async () => {
    filesApi.listFiles.mockResolvedValueOnce([textFile]);
    const user = userEvent.setup();
    render(<FilesPanel onClose={vi.fn()} />);

    await user.click(await screen.findByText("notes.txt"));
    expect(filesApi.downloadFile).toHaveBeenCalledWith(textFile.id, textFile.original_filename);
    expect(filesApi.fetchFileBlob).not.toHaveBeenCalled();
  });

  it("calls onClose when the close button is selected", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<FilesPanel onClose={onClose} />);
    await screen.findByText("لا توجد ملفات بعد");

    await user.click(screen.getByRole("button", { name: "✕" }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
