import api from "./api";

export async function uploadFile(file, onProgress) {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await api.post("/files/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (event) => {
      if (onProgress && event.total) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    },
  });
  return data;
}

export async function listFiles() {
  const { data } = await api.get("/files");
  return data;
}

export async function deleteFile(id) {
  await api.delete(`/files/${id}`);
}

// نحمّل الملف عبر Axios حتى تُرسل Cookies الجلسة مع الطلب؛
// رابط <a> مباشر لا يسمح بضبط إعدادات الاعتماد بشكل صريح.
export async function fetchFileBlob(id) {
  const response = await api.get(`/files/${id}`, { responseType: "blob" });
  return response.data;
}

export async function downloadFile(id, filename) {
  const blob = await fetchFileBlob(id);
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
