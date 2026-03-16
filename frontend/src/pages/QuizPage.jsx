import React from "react";
import { Container, Typography } from "@mui/material";

/**
 * QuizPage -- quiz generation, taking, and results.
 *
 * TODO (Phase 4+): Material selection summary, quiz options (questions/difficulty/type),
 * Generate Quiz button, loading state, QuizView, Submit button,
 * score summary, retry option. Uses useQuiz hook.
 */
function QuizPage() {
  return (
    <Container maxWidth="md" sx={{ mt: 4 }}>
      <Typography variant="h1" gutterBottom>
        Quiz
      </Typography>
      <Typography variant="body1" color="text.secondary">
        Select materials and generate a personalized quiz.
      </Typography>
    </Container>
  );
}

export default QuizPage;
