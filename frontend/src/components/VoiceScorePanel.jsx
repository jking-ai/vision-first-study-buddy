import React, { useState, useEffect } from "react";
import {
  Card,
  CardContent,
  Typography,
  Chip,
  Stack,
  Box,
  Alert,
  Collapse,
  IconButton,
  Paper,
} from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CancelIcon from "@mui/icons-material/Cancel";
import EmojiEventsIcon from "@mui/icons-material/EmojiEvents";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

/**
 * Quiz progress: score chip, tutor summary, and per-answer feedback.
 *
 * Pass `collapsible` during a live session so the answer list starts folded
 * and the conversation stays front and centre; it expands automatically when
 * the quiz summary arrives.
 */
export function VoiceScorePanel({ score, answers = [], quizSummary, collapsible = false }) {
  const [open, setOpen] = useState(!collapsible);

  useEffect(() => {
    if (quizSummary) setOpen(true);
  }, [quizSummary]);

  if (!score && answers.length === 0 && !quizSummary) {
    return null;
  }

  const correct = score?.correct ?? 0;
  const total = score?.total ?? 5;
  const answered = answers.length;

  const answerList = (
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
              <Typography variant="subtitle2" sx={{ fontWeight: 600, flex: 1 }}>
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
  );

  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        spacing={1}
        onClick={collapsible ? () => setOpen((o) => !o) : undefined}
        sx={{ cursor: collapsible ? "pointer" : "default" }}
      >
        <Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
            Quiz progress
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {answered} of {total} answered
          </Typography>
        </Box>
        <Stack direction="row" alignItems="center" spacing={1}>
          {score && (
            <Chip
              icon={<EmojiEventsIcon />}
              label={`${correct} / ${total}`}
              color={correct >= total / 2 ? "success" : "default"}
              sx={{ fontWeight: 600 }}
            />
          )}
          {collapsible && (
            <IconButton
              size="small"
              aria-label={open ? "hide answers" : "show answers"}
              aria-expanded={open}
              sx={{
                transform: open ? "rotate(180deg)" : "rotate(0deg)",
                transition: "transform 0.2s",
              }}
            >
              <ExpandMoreIcon />
            </IconButton>
          )}
        </Stack>
      </Stack>

      <Collapse in={open}>
        <Box sx={{ mt: 2 }}>
          {quizSummary && (
            <Alert severity="info" sx={{ mb: answers.length > 0 ? 2 : 0 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                Tutor summary
              </Typography>
              <Typography variant="body2">{quizSummary}</Typography>
            </Alert>
          )}
          {answers.length > 0 && answerList}
        </Box>
      </Collapse>
    </Paper>
  );
}

export default VoiceScorePanel;
