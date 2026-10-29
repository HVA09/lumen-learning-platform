import api from "./api";

export async function listTopicQuestions(topicId) {
  const { data } = await api.get(`/content/topics/${topicId}/questions`);
  return data;
}

export async function createQuestion(topicId, payload) {
  const { data } = await api.post(`/content/topics/${topicId}/questions`, payload);
  return data;
}

export async function updateQuestion(questionId, payload) {
  const { data } = await api.put(`/content/questions/${questionId}`, payload);
  return data;
}

export async function deleteQuestion(questionId) {
  await api.delete(`/content/questions/${questionId}`);
}

export async function listTopicLessonsForTeacher(topicId) {
  const { data } = await api.get(`/content/topics/${topicId}/lessons`);
  return data;
}

export async function createLesson(topicId, payload) {
  const { data } = await api.post(`/content/topics/${topicId}/lessons`, payload);
  return data;
}

export async function updateLesson(lessonId, payload) {
  const { data } = await api.put(`/content/lessons/${lessonId}`, payload);
  return data;
}

export async function deleteLesson(lessonId) {
  await api.delete(`/content/lessons/${lessonId}`);
}

export async function getTopicAnalytics(topicId) {
  const { data } = await api.get(`/content/topics/${topicId}/analytics`);
  return data;
}
