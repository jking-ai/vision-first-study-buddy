import { describe, it, expect, beforeEach } from "vitest";
import { getQuizHistory, saveQuizResult, clearQuizHistory } from "./quizHistory";

describe("quizHistory", () => {
  beforeEach(() => {
    clearQuizHistory();
  });

  it("saveQuizResult({...}) without mode stores 'written'", () => {
    saveQuizResult({
      quizId: "q_1",
      title: "Written Quiz",
      score: 4,
      total: 5,
      percentage: 80,
    });

    const history = getQuizHistory();
    expect(history.length).toBe(1);
    expect(history[0].mode).toBe("written");
    expect(history[0].title).toBe("Written Quiz");
  });

  it("saveQuizResult({...}) with mode: 'voice' stores 'voice'", () => {
    saveQuizResult({
      quizId: "vs_1",
      title: "Voice Quiz",
      score: 5,
      total: 5,
      percentage: 100,
      mode: "voice",
    });

    const history = getQuizHistory();
    expect(history.length).toBe(1);
    expect(history[0].mode).toBe("voice");
    expect(history[0].score).toBe(5);
  });
});
