import api from "./api";

export async function getSubjects() {
  const { data } = await api.get("/curriculum/subjects");
  return data;
}

export async function getLearningPath() {
  const { data } = await api.get("/curriculum/path");
  return data;
}

export async function getTopic(topicId) {
  const { data } = await api.get(`/curriculum/topics/${topicId}`);
  return data;
}

export async function getTopicMastery(topicId) {
  const { data } = await api.get(`/curriculum/topics/${topicId}/mastery`);
  return data;
}

export async function getTopicLessons(topicId) {
  const { data } = await api.get(`/curriculum/topics/${topicId}/lessons`);
  return data;
}

export async function completeLesson(lessonId) {
  const { data } = await api.post(`/curriculum/lessons/${lessonId}/complete`);
  return data;
}
