import { useEffect, useState } from "react";
import { addDeck, getDecks, getDueCards, submitReview } from "../lib/srsApi";
import MathText from "./MathText";

function DeckBrowser({ onClose, onStartReview }) {
  const [decks, setDecks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [addingTopicId, setAddingTopicId] = useState(null);
  const [error, setError] = useState("");

  const refresh = () => {
    setLoading(true);
    getDecks()
      .then(setDecks)
      .catch(() => setError("تعذر تحميل المجموعات"))
      .finally(() => setLoading(false));
  };

  useEffect(refresh, []);

  const handleAdd = async (topicId) => {
    setAddingTopicId(topicId);
    try {
      await addDeck(topicId);
      refresh();
    } catch {
      setError("تعذر إضافة المجموعة");
    } finally {
      setAddingTopicId(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/30 p-4">
      <div className="my-8 w-full max-w-md rounded-3xl border border-slate-200 bg-white p-6 shadow-lg">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">مجموعات البطاقات الجاهزة</h2>
          <button
            onClick={onClose}
            className="rounded-lg px-2 py-1 text-slate-400 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400"
          >
            ✕
          </button>
        </div>

        <button
          onClick={onStartReview}
          className="mb-4 w-full rounded-xl bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-800"
        >
          🔁 راجع البطاقات المستحقة الآن
        </button>

        {error && <p className="mb-2 text-sm text-red-600">{error}</p>}
        {loading ? (
          <p className="text-sm text-slate-400">...</p>
        ) : (
          <div className="space-y-2">
            {decks.map((deck) => (
              <div
                key={deck.topic_id}
                className="flex items-center justify-between rounded-xl border border-slate-200 px-3 py-2 text-sm"
              >
                <div>
                  <p className="text-slate-900">{deck.topic_name_ar}</p>
                  <p className="text-xs text-slate-400">
                    {deck.added_cards}/{deck.total_cards} مضافة
                  </p>
                </div>
                <button
                  onClick={() => handleAdd(deck.topic_id)}
                  disabled={addingTopicId === deck.topic_id || deck.added_cards === deck.total_cards}
                  className="shrink-0 rounded-lg border border-slate-200 px-3 py-1.5 text-xs hover:bg-slate-50 disabled:opacity-50"
                >
                  {deck.added_cards === deck.total_cards
                    ? "أُضيفت ✓"
                    : addingTopicId === deck.topic_id
                    ? "..."
                    : "أضِف للبطاقات"}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ReviewSession({ onClose }) {
  const [cards, setCards] = useState([]);
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [loading, setLoading] = useState(true);
  const [reviewedCount, setReviewedCount] = useState(0);

  useEffect(() => {
    getDueCards()
      .then(setCards)
      .finally(() => setLoading(false));
  }, []);

  const currentCard = cards[index];

  const handleGrade = async (grade) => {
    if (!currentCard) return;
    try {
      await submitReview(currentCard.id, grade);
    } catch {
      // نكمل حتى لو فشل حفظ التقييم — أهم شي الطالب يكمل مراجعته بدون توقف
    }
    setReviewedCount((c) => c + 1);
    setFlipped(false);
    setIndex((i) => i + 1);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
      <div className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-6 shadow-lg">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">مراجعة البطاقات</h2>
          <button
            onClick={onClose}
            className="rounded-lg px-2 py-1 text-slate-400 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400"
          >
            ✕
          </button>
        </div>

        {loading ? (
          <p className="text-sm text-slate-400">...</p>
        ) : !currentCard ? (
          <div className="py-8 text-center">
            <p className="text-slate-700">
              {reviewedCount > 0 ? "خلّصت كل البطاقات المستحقة اليوم 🎉" : "ما فيه بطاقات مستحقة الآن"}
            </p>
            <button
              onClick={onClose}
              className="mt-4 rounded-xl bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-800"
            >
              إغلاق
            </button>
          </div>
        ) : (
          <>
            <p className="mb-3 text-center text-xs text-slate-400">
              بطاقة {index + 1} من {cards.length}
            </p>
            <div
              onClick={() => setFlipped((f) => !f)}
              className="flex min-h-40 cursor-pointer items-center justify-center rounded-2xl border border-slate-200 bg-slate-50 p-6 text-center"
            >
              <MathText className="whitespace-pre-line text-lg text-slate-900">
                {flipped ? currentCard.back_text : currentCard.front_text}
              </MathText>
            </div>
            {!flipped ? (
              <button
                onClick={() => setFlipped(true)}
                className="mt-4 w-full rounded-xl bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-800"
              >
                اعرض الجواب
              </button>
            ) : (
              <div className="mt-4 grid grid-cols-3 gap-2">
                <button
                  onClick={() => handleGrade("again")}
                  className="rounded-xl border border-red-200 px-3 py-2 text-sm text-red-600 hover:bg-red-50"
                >
                  ما عرفت
                </button>
                <button
                  onClick={() => handleGrade("good")}
                  className="rounded-xl border border-slate-200 px-3 py-2 text-sm hover:bg-slate-50"
                >
                  عرفت
                </button>
                <button
                  onClick={() => handleGrade("easy")}
                  className="rounded-xl border border-emerald-200 px-3 py-2 text-sm text-emerald-700 hover:bg-emerald-50"
                >
                  سهلة
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default function FlashcardReview({ onClose }) {
  const [reviewing, setReviewing] = useState(false);

  if (reviewing) return <ReviewSession onClose={onClose} />;
  return <DeckBrowser onClose={onClose} onStartReview={() => setReviewing(true)} />;
}
