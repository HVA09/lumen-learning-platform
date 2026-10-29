import api from "./api";

export async function getLeaderboard(classId = null) {
  const { data } = await api.get("/gamification/leaderboard", {
    params: classId ? { class_id: classId } : {},
  });
  return data;
}

export async function getMyAchievements() {
  const { data } = await api.get("/gamification/my-achievements");
  return data;
}

export async function getMyStats() {
  const { data } = await api.get("/gamification/my-stats");
  return data;
}
