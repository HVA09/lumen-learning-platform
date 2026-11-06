import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  post: vi.fn(),
  get: vi.fn(),
  delete: vi.fn(),
}));

vi.mock("./api", () => ({ default: api }));

import { deleteFile, downloadFile, fetchFileBlob, listFiles, uploadFile } from "./filesApi";

describe("file API adapters", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("uploads a file and reports rounded progress percentages", async () => {
    const file = new File(["lesson"], "lesson.pdf", { type: "application/pdf" });
    const onProgress = vi.fn();
    api.post.mockImplementation(async (_url, formData, options) => {
      options.onUploadProgress({ loaded: 1, total: 3 });
      options.onUploadProgress({ loaded: 3, total: 3 });
      return { data: { id: 12 } };
    });

    await expect(uploadFile(file, onProgress)).resolves.toEqual({ id: 12 });
    const [url, formData, options] = api.post.mock.calls[0];
    expect(url).toBe("/files/upload");
    expect(formData).toBeInstanceOf(FormData);
    expect(formData.get("file")).toBe(file);
    expect(options.headers).toEqual({ "Content-Type": "multipart/form-data" });
    expect(onProgress).toHaveBeenNthCalledWith(1, 33);
    expect(onProgress).toHaveBeenNthCalledWith(2, 100);
  });

  it("does not report upload progress without a callback or a known total", async () => {
    api.post.mockImplementation(async (_url, _formData, options) => {
      options.onUploadProgress({ loaded: 5, total: 0 });
      return { data: { id: 13 } };
    });
    const file = new File(["x"], "x.txt", { type: "text/plain" });

    await uploadFile(file);
    expect(api.post).toHaveBeenCalledTimes(1);
  });

  it("lists and deletes files using their API routes", async () => {
    const files = [{ id: 4, filename: "notes.pdf" }];
    api.get.mockResolvedValueOnce({ data: files });
    api.delete.mockResolvedValueOnce({});

    await expect(listFiles()).resolves.toEqual(files);
    await expect(deleteFile(4)).resolves.toBeUndefined();
    expect(api.get).toHaveBeenCalledWith("/files");
    expect(api.delete).toHaveBeenCalledWith("/files/4");
  });

  it("fetches file content as a blob through the authenticated API client", async () => {
    const blob = new Blob(["private course file"], { type: "application/pdf" });
    api.get.mockResolvedValueOnce({ data: blob });

    await expect(fetchFileBlob(9)).resolves.toBe(blob);
    expect(api.get).toHaveBeenCalledWith("/files/9", { responseType: "blob" });
  });

  it("downloads a blob with a temporary object URL and revokes it afterwards", async () => {
    const blob = new Blob(["report"]);
    const createObjectURL = vi.fn(() => "blob:lumen-test");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { createObjectURL, revokeObjectURL });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    api.get.mockResolvedValueOnce({ data: blob });

    await downloadFile(21, "report.pdf");

    expect(api.get).toHaveBeenCalledWith("/files/21", { responseType: "blob" });
    expect(createObjectURL).toHaveBeenCalledWith(blob);
    expect(HTMLAnchorElement.prototype.click).toHaveBeenCalledTimes(1);
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:lumen-test");
  });
});
