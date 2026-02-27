import React, { useState } from "react";
import { useLocation } from "react-router-dom";
import {
  Container,
  Typography,
  Button,
  Alert,
  Box,
  CircularProgress,
  Slider,
  ToggleButton,
  ToggleButtonGroup,
  FormGroup,
  FormControlLabel,
  Checkbox,
  Divider,
  Card,
  CardContent,
  Stack,
  Chip,
  IconButton,
  LinearProgress,
} from "@mui/material";
import Grid from "@mui/material/Grid2";
import QuizIcon from "@mui/icons-material/Quiz";
import DeleteIcon from "@mui/icons-material/Delete";
import DeleteSweepIcon from "@mui/icons-material/DeleteSweep";
import HistoryIcon from "@mui/icons-material/History";
import QuizView from "../components/QuizView";
import MaterialList from "../components/MaterialList";
import useQuiz from "../hooks/useQuiz";
import useMaterials from "../hooks/useMaterials";

function getScoreColor(percentage) {
  if (percentage >= 80) return "success";
  if (percentage >= 60) return "warning";
  return "error";
}

function QuizPage() {
  const location = useLocation();
  const passedIds = location.state?.selectedIds || [];

  const { materials, loading: materialsLoading } = useMaterials();
  const {
    generateQuiz,
    submitAnswers,
    quiz,
    results,
    loading,
    submitting,
    error,
    reset,
    history,
    clearHistory,
    deleteHistoryItem,
  } = useQuiz();

  const [selectedIds, setSelectedIds] = useState(passedIds);
  const [numQuestions, setNumQuestions] = useState(10);
  const [difficulty, setDifficulty] = useState("mixed");
  const [questionTypes, setQuestionTypes] = useState({
    multiple_choice: true,
    short_answer: true,
    true_false: false,
  });

  const activeTypes = Object.entries(questionTypes)
    .filter(([, v]) => v)
    .map(([k]) => k);

  const handleGenerate = () => {
    if (selectedIds.length === 0 || activeTypes.length === 0) return;
    generateQuiz(selectedIds, numQuestions, difficulty, activeTypes);
  };

  const handleSubmit = (quizId, answers) => {
    submitAnswers(quizId, answers);
  };

  const toggleType = (type) => {
    setQuestionTypes((prev) => ({ ...prev, [type]: !prev[type] }));
  };

  if (quiz) {
    return (
      <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
        <Button onClick={reset} sx={{ mb: 2 }}>
          Generate New Quiz
        </Button>
        <Typography variant="h1" gutterBottom>
          {quiz.title}
        </Typography>
        {submitting && (
          <Box sx={{ textAlign: "center", py: 3 }}>
            <CircularProgress />
            <Typography sx={{ mt: 1 }}>Grading your answers...</Typography>
          </Box>
        )}
        {!submitting && (
          <QuizView quiz={quiz} onSubmit={handleSubmit} results={results} />
        )}
        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}
      </Container>
    );
  }

  return (
    <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h1" gutterBottom>
        Quiz
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Select materials and configure quiz options.
      </Typography>

      {passedIds.length === 0 && (
        <>
          <Typography variant="h6" sx={{ mb: 1 }}>
            Select Materials
          </Typography>
          <MaterialList
            materials={materials}
            selectedIds={selectedIds}
            onSelectionChange={setSelectedIds}
            loading={materialsLoading}
          />
          <Divider sx={{ my: 3 }} />
        </>
      )}

      {passedIds.length > 0 && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {selectedIds.length} material{selectedIds.length !== 1 ? "s" : ""} selected from Materials page.
        </Typography>
      )}

      <Box sx={{ mb: 3 }}>
        <Typography variant="body2" sx={{ mb: 1 }}>
          Number of Questions: {numQuestions}
        </Typography>
        <Slider
          value={numQuestions}
          onChange={(_, val) => setNumQuestions(val)}
          min={5}
          max={25}
          step={1}
          marks={[
            { value: 5, label: "5" },
            { value: 10, label: "10" },
            { value: 15, label: "15" },
            { value: 20, label: "20" },
            { value: 25, label: "25" },
          ]}
          sx={{ mb: 3 }}
        />

        <Typography variant="body2" sx={{ mb: 1 }}>
          Difficulty
        </Typography>
        <ToggleButtonGroup
          value={difficulty}
          exclusive
          onChange={(_, val) => val && setDifficulty(val)}
          size="small"
          sx={{ mb: 3 }}
        >
          <ToggleButton value="easy">Easy</ToggleButton>
          <ToggleButton value="medium">Medium</ToggleButton>
          <ToggleButton value="hard">Hard</ToggleButton>
          <ToggleButton value="mixed">Mixed</ToggleButton>
        </ToggleButtonGroup>

        <Typography variant="body2" sx={{ mb: 1, display: "block" }}>
          Question Types
        </Typography>
        <FormGroup row>
          <FormControlLabel
            control={<Checkbox checked={questionTypes.multiple_choice} onChange={() => toggleType("multiple_choice")} />}
            label="Multiple Choice"
          />
          <FormControlLabel
            control={<Checkbox checked={questionTypes.short_answer} onChange={() => toggleType("short_answer")} />}
            label="Short Answer"
          />
          <FormControlLabel
            control={<Checkbox checked={questionTypes.true_false} onChange={() => toggleType("true_false")} />}
            label="True / False"
          />
        </FormGroup>
      </Box>

      <Button
        variant="contained"
        size="large"
        startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <QuizIcon />}
        onClick={handleGenerate}
        disabled={selectedIds.length === 0 || activeTypes.length === 0 || loading}
      >
        {loading ? "Generating..." : "Generate Quiz"}
      </Button>

      {error && (
        <Alert severity="error" sx={{ mt: 2 }} onClose={() => reset()}>
          {error}
        </Alert>
      )}

      {history.length > 0 && (
        <>
          <Divider sx={{ my: 4 }} />
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
            <Stack direction="row" alignItems="center" spacing={1}>
              <HistoryIcon color="action" />
              <Typography variant="h6">Score History</Typography>
            </Stack>
            <Button
              size="small"
              color="error"
              startIcon={<DeleteSweepIcon />}
              onClick={clearHistory}
            >
              Clear All
            </Button>
          </Stack>
          <Grid container spacing={2}>
            {history.map((entry) => (
              <Grid key={entry.id} size={{ xs: 12, sm: 6 }}>
                <Card variant="outlined">
                  <CardContent sx={{ pb: "12px !important" }}>
                    <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                      <Box sx={{ flex: 1, minWidth: 0, mr: 1 }}>
                        <Typography variant="subtitle2" noWrap title={entry.title}>
                          {entry.title}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {new Date(entry.date).toLocaleDateString()}{" "}
                          {new Date(entry.date).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                        </Typography>
                      </Box>
                      <Stack direction="row" alignItems="center" spacing={1}>
                        <Chip
                          label={`${entry.score}/${entry.total}`}
                          size="small"
                          color={getScoreColor(entry.percentage)}
                          variant="outlined"
                        />
                        <IconButton
                          size="small"
                          onClick={() => deleteHistoryItem(entry.id)}
                          title="Delete"
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Stack>
                    </Stack>
                    <Box sx={{ mt: 1.5 }}>
                      <LinearProgress
                        variant="determinate"
                        value={entry.percentage}
                        color={getScoreColor(entry.percentage)}
                        sx={{ height: 6, borderRadius: 1 }}
                      />
                      <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: "block" }}>
                        {entry.percentage}%
                      </Typography>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </>
      )}
    </Container>
  );
}

export default QuizPage;
