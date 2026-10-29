import api from "./api";

export async function getDueCards() {
  const { data } = await api.get("/srs/due");
  return data;
}

export async function submitReview(cardId, grade) {
  const { data } = await api.post(`/srs/cards/${cardId}/review`, { grade });
  return data;
}

export async function createCard(frontText, backText, topicId = null) {
  const { data } = await api.post("/srs/cards", {
    front_text: frontText,
    back_text: backText,
    topic_id: topicId,
  });
  return data;
}

export async function getDecks() {
  const { data } = await api.get("/srs/decks");
  return data;
}

export async function addDeck(topicId) {
  const { data } = await api.post(`/srs/decks/${topicId}/add`);
  return data;
}
