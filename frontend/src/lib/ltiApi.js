import api from "./api";

export async function listLtiPlatforms() {
  const { data } = await api.get("/lti/platforms");
  return data;
}

export async function registerLtiPlatform(payload) {
  const { data } = await api.post("/lti/platforms", payload);
  return data;
}

export async function listDiscoveredResourceLinks() {
  const { data } = await api.get("/lti/resource-links");
  return data;
}

export async function listLtiAssignmentLinks() {
  const { data } = await api.get("/lti/assignment-links");
  return data;
}

export async function createLtiAssignmentLink(payload) {
  const { data } = await api.post("/lti/assignment-links", payload);
  return data;
}

export async function listLtiGradeEvents() {
  const { data } = await api.get("/lti/grade-events");
  return data;
}

export async function retryLtiGradeEvent(eventId) {
  const { data } = await api.post(\`/lti/grade-events/\${eventId}/retry\`);
  return data;
}
