import api from "./api";

export async function startQuiz(topicId, mode = "practice") {
  const { data } = await api.post(`/quiz/topics/${topicId}/start`, { mode });
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
