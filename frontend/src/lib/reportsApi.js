import api from "./api";

export async function getMyProgress() {
  const { data } = await api.get("/reports/my-progress");
  return data;
}

export async function sendMyReport() {
  const { data } = await api.post("/reports/send-my-report");
  return data;
}
