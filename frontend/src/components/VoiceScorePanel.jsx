import React from "react";
import {
  Card,
  CardContent,
  Typography,
  Chip,
  Stack,
  Box,
  Divider,
  Alert,
} from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CancelIcon from "@mui/icons-material/Cancel";
import EmojiEventsIcon from "@mui/icons-material/EmojiEvents";

export function VoiceScorePanel({ score, answers = [], quizSummary }) {
  if (!score && answers.length === 0 && !quizSummary) {
    return null;
  }

  const correct = score?.correct ?? 0;
  const total = score?.total ?? 5;

  return (
    <Box sx={{ my: 3 }}>
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        sx={{ mb: 2 }}
      >
        <Typography variant="h6">Oral Quiz Progress</Typography>
        {score && (
          <Chip
            icon={<EmojiEventsIcon />}
            label={`Score: ${correct} / ${total}`}
            color={correct >= total / 2 ? "success" : "default"}
            variant="filled"
            sx={{ fontWeight: "bold" }}
          />
        )}
      </Stack>

      {quizSummary && (
        <Alert severity="info" sx={{ mb: 2 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: "bold" }}>
            Coach Summary:
          </Typography>
          <Typography variant="body2">{quizSummary}</Typography>
        </Alert>
      )}

      {answers.length > 0 && (
        <Stack spacing={1.5}>
          {answers.map((ans, idx) => (
            <Card key={idx} variant="outlined">
              <CardContent sx={{ py: 1.5, px: 2, "&:last-child": { pb: 1.5 } }}>
                <Stack
                  direction="row"
                  justifyContent="space-between"
                  alignItems="flex-start"
                  spacing={1}
                >
                  <Typography variant="subtitle2" sx={{ fontWeight: "bold", flex: 1 }}>
                    {ans.index}. {ans.question}
                  </Typography>
                  <Chip
                    icon={ans.correct ? <CheckCircleIcon /> : <CancelIcon />}
                    label={ans.correct ? "Correct" : "Incorrect"}
                    size="small"
                    color={ans.correct ? "success" : "error"}
                    variant="outlined"
                  />
                </Stack>

                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ mt: 1, fontStyle: "italic" }}
                >
                  Your answer: "{ans.student_answer}"
                </Typography>

                {ans.feedback && (
                  <Typography variant="body2" sx={{ mt: 0.5 }}>
                    <strong>Feedback:</strong> {ans.feedback}
                  </Typography>
                )}
              </CardContent>
            </Card>
          ))}
        </Stack>
      )}
    </Box>
  );
}

export default VoiceScorePanel;
