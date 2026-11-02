import api from "./api";

export async function getAssignments() {
  const { data } = await api.get("/assignments");
  return data;
}

export async function getAssignment(assignmentId) {
  const { data } = await api.get(`/assignments/${assignmentId}`);
  return data;
}

export async function createAssignment(payload) {
  const { data } = await api.post("/assignments", payload);
  return data;
}

export async function deleteAssignment(assignmentId) {
  await api.delete(`/assignments/${assignmentId}`);
}

export async function getMySubmission(assignmentId) {
  const { data } = await api.get(`/assignments/${assignmentId}/my-submission`);
  return data;
}

export async function submitAssignment(assignmentId, writtenAnswer) {
  const { data } = await api.post(`/assignments/${assignmentId}/submit`, {
    written_answer: writtenAnswer,
  });
  return data;
}

export async function listSubmissions(assignmentId) {
  const { data } = await api.get(`/assignments/${assignmentId}/submissions`);
  return data;
}

export async function gradeSubmission(assignmentId, submissionId, gradePercentage, feedback) {
  const { data } = await api.post(
    `/assignments/${assignmentId}/submissions/${submissionId}/grade`,
    { grade_percentage: gradePercentage, feedback }
  );
  return data;
}
