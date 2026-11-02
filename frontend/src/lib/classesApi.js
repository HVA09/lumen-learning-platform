import api from "./api";

export async function listClasses() {
  const { data } = await api.get("/classes");
  return data;
}

export async function getClassDetail(classId) {
  const { data } = await api.get(`/classes/${classId}`);
  return data;
}

export async function createClass(name) {
  const { data } = await api.post("/classes", { name });
  return data;
}

export async function renameClass(classId, name) {
  const { data } = await api.patch(`/classes/${classId}`, { name });
  return data;
}

export async function regenerateInviteCode(classId) {
  const { data } = await api.post(`/classes/${classId}/regenerate-code`);
  return data;
}

export async function deleteClass(classId) {
  await api.delete(`/classes/${classId}`);
}

export async function removeStudentFromClass(classId, studentUserId) {
  await api.delete(`/classes/${classId}/students/${studentUserId}`);
}

export async function joinClass(inviteCode) {
  const { data } = await api.post("/classes/join", { invite_code: inviteCode });
  return data;
}
