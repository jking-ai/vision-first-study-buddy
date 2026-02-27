import React, { useState } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  RadioGroup,
  Radio,
  FormControlLabel,
  TextField,
  Button,
  Chip,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  LinearProgress,
  Paper,
  Stack,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CancelIcon from "@mui/icons-material/Cancel";

function QuizView({ quiz, onSubmit, results }) {
  const [answers, setAnswers] = useState({});

  if (!quiz) return null;

  const questions = quiz.questions || [];
  const answeredCount = Object.keys(answers).length;
  const allAnswered = answeredCount === questions.length;

  const setAnswer = (questionId, value) => {
    setAnswers((prev) => ({ ...prev, [questionId]: value }));
  };

  const handleSubmit = () => {
    const formatted = questions.map((q) => ({
      question_id: q.id,
      answer: answers[q.id] || "",
    }));
    onSubmit?.(quiz.id, formatted);
  };

  // Results mode
  if (results) {
    const { score, results: questionResults } = results;
    const percentage = score?.percentage ?? 0;
    const color = percentage >= 80 ? "success" : percentage >= 50 ? "warning" : "error";

    return (
      <Box>
        {/* Score summary */}
        <Paper sx={{ p: 3, mb: 3, textAlign: "center" }}>
          <Typography variant="h4" color={`${color}.main`} gutterBottom>
            {score.correct} / {score.total}
          </Typography>
          <LinearProgress
            variant="determinate"
            value={percentage}
            color={color}
            sx={{ height: 10, borderRadius: 5, mb: 1 }}
          />
          <Typography variant="body1" color="text.secondary">
            {percentage.toFixed(0)}% correct
          </Typography>
        </Paper>

        {/* Question results */}
        {questions.map((q, i) => {
          const result = questionResults?.find((r) => r.question_id === q.id);
          const isCorrect = result?.is_correct;

          return (
            <Card
              key={q.id}
              sx={{
                mb: 2,
                borderLeft: 4,
                borderColor: isCorrect ? "success.main" : "error.main",
              }}
            >
              <CardContent>
                <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                  {isCorrect ? (
                    <CheckCircleIcon color="success" />
                  ) : (
                    <CancelIcon color="error" />
                  )}
                  <Typography variant="body2" color="text.secondary">
                    Question {i + 1}
                  </Typography>
                  <Chip label={q.difficulty} size="small" variant="outlined" />
                </Stack>

                <Typography variant="body1" sx={{ mb: 1 }}>
                  {q.question}
                </Typography>

                {/* Show submitted vs correct */}
                {result && (
                  <Box sx={{ mt: 1 }}>
                    <Typography variant="body2">
                      <strong>Your answer:</strong> {result.submitted_answer || "(no answer)"}
                    </Typography>
                    {!isCorrect && (
                      <Typography variant="body2" color="success.main">
                        <strong>Correct answer:</strong> {result.correct_answer}
                      </Typography>
                    )}
                  </Box>
                )}

                {/* Explanation */}
                {result?.explanation && (
                  <Accordion sx={{ mt: 1 }}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Typography variant="body2">Explanation</Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Typography variant="body2">{result.explanation}</Typography>
                    </AccordionDetails>
                  </Accordion>
                )}
              </CardContent>
            </Card>
          );
        })}

        <Button variant="contained" onClick={() => window.location.reload()} sx={{ mt: 2 }}>
          Try Again
        </Button>
      </Box>
    );
  }

  // Taking mode
  return (
    <Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {answeredCount} of {questions.length} answered
      </Typography>

      {questions.map((q, i) => (
        <Card key={q.id} sx={{ mb: 2 }}>
          <CardContent>
            <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
              <Typography variant="body2" color="text.secondary">
                Question {i + 1}
              </Typography>
              <Chip label={q.difficulty} size="small" variant="outlined" />
              <Chip label={q.type.replace("_", " ")} size="small" />
            </Stack>

            <Typography variant="body1" sx={{ mb: 2 }}>
              {q.question}
            </Typography>

            {/* Multiple choice / True-false */}
            {(q.type === "multiple_choice" || q.type === "true_false") && q.options?.length > 0 && (
              <RadioGroup
                value={answers[q.id] || ""}
                onChange={(e) => setAnswer(q.id, e.target.value)}
              >
                {q.options.map((opt, j) => (
                  <FormControlLabel
                    key={j}
                    value={opt.charAt(0)}
                    control={<Radio />}
                    label={opt}
                  />
                ))}
              </RadioGroup>
            )}

            {/* True/false without options */}
            {q.type === "true_false" && (!q.options || q.options.length === 0) && (
              <RadioGroup
                value={answers[q.id] || ""}
                onChange={(e) => setAnswer(q.id, e.target.value)}
              >
                <FormControlLabel value="True" control={<Radio />} label="True" />
                <FormControlLabel value="False" control={<Radio />} label="False" />
              </RadioGroup>
            )}

            {/* Short answer */}
            {q.type === "short_answer" && (
              <TextField
                fullWidth
                multiline
                minRows={2}
                placeholder="Type your answer..."
                value={answers[q.id] || ""}
                onChange={(e) => setAnswer(q.id, e.target.value)}
              />
            )}
          </CardContent>
        </Card>
      ))}

      <Button
        variant="contained"
        size="large"
        disabled={!allAnswered}
        onClick={handleSubmit}
        sx={{ mt: 1 }}
      >
        Submit Answers
      </Button>
      {!allAnswered && (
        <Typography variant="caption" color="text.secondary" sx={{ ml: 2 }}>
          Answer all questions to submit
        </Typography>
      )}
    </Box>
  );
}

export default QuizView;
