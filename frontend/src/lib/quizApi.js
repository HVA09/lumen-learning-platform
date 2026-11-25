import api from "./api";

export async function startQuiz(topicId, mode = "practice", classSectionId) {
  const payload = { mode };
  if (classSectionId !== undefined) payload.class_section_id = classSectionId;
  const { data } = await api.post(`/quiz/topics/${topicId}/start`, payload);
  return data;
}

export async function saveDraftAnswers(attemptId, answers) {
  const { data } = await api.put(`/quiz/attempts/${attemptId}/answers`, { answers });
  return data;
}

export async function submitQuiz(attemptId, answers) {
  const { data } = await api.post(`/quiz/attempts/${attemptId}/submit`, { answers });
  return data;
}

export async function getQuizHistory(topicId) {
  const { data } = await api.get(`/quiz/topics/${topicId}/history`);
  return data;
}
