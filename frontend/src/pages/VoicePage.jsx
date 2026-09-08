import React, { useState, useEffect, useMemo } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  Container,
  Typography,
  Box,
  Button,
  Paper,
  Alert,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Stack,
  Chip,
  Divider,
} from "@mui/material";
import RecordVoiceOverIcon from "@mui/icons-material/RecordVoiceOver";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import RefreshIcon from "@mui/icons-material/Refresh";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";

import { useVoiceSession } from "../hooks/useVoiceSession";
import { getSavedStudyGuides } from "../utils/studyGuideStorage";
import VoiceControls from "../components/VoiceControls";
import VoiceTranscript from "../components/VoiceTranscript";
import VoiceScorePanel from "../components/VoiceScorePanel";

export function VoicePage() {
  const location = useLocation();
  const navigate = useNavigate();

  const passedGuide = location.state?.studyGuide || null;
  const [savedGuides, setSavedGuides] = useState([]);
  const [selectedGuideId, setSelectedGuideId] = useState(
    passedGuide ? passedGuide.id : ""
  );

  useEffect(() => {
    const list = getSavedStudyGuides();
    setSavedGuides(list);
    if (!passedGuide && list.length > 0 && !selectedGuideId) {
      setSelectedGuideId(list[0].id);
    }
  }, [passedGuide, selectedGuideId]);

  const activeStudyGuide = useMemo(() => {
    if (passedGuide && (!selectedGuideId || selectedGuideId === passedGuide.id)) {
      return passedGuide;
    }
    const found = savedGuides.find((g) => g.id === selectedGuideId);
    return found ? found.studyGuide : passedGuide;
  }, [passedGuide, savedGuides, selectedGuideId]);

  const {
    state,
    status,
    transcript,
    secondsLeft,
    error,
    endedReason,
    answers,
    quizSummary,
    score,
    start,
    pressTalk,
    releaseTalk,
    end,
    refreshStatus,
  } = useVoiceSession({ studyGuide: activeStudyGuide });

  const remainingToday = status?.remaining_today ?? 0;
  const isEnabled = status?.enabled ?? false;
  const canStartSession = isEnabled && remainingToday > 0 && !!activeStudyGuide;

  const endedReasonText = useMemo(() => {
    switch (endedReason) {
      case "quiz_complete":
        return "Quiz complete!";
      case "max_duration":
        return "Time's up";
      case "idle_timeout":
        return "Session ended after inactivity";
      case "upstream_closed":
        return "The coach disconnected";
      case "client_end":
      default:
        return "Session complete";
    }
  }, [endedReason]);

  // Loading state
  if (status === null && state === "idle") {
    return (
      <Container maxWidth="md" sx={{ mt: 6, textAlign: "center" }}>
        <CircularProgress />
        <Typography variant="body1" sx={{ mt: 2 }} color="text.secondary">
          Checking voice availability…
        </Typography>
      </Container>
    );
  }

  // Empty state: no guide selected or available
  if (!activeStudyGuide && savedGuides.length === 0) {
    return (
      <Container maxWidth="md" sx={{ mt: 6 }}>
        <Paper variant="outlined" sx={{ p: 4, textAlign: "center" }}>
          <RecordVoiceOverIcon sx={{ fontSize: 64, color: "primary.main", mb: 2 }} />
          <Typography variant="h5" gutterBottom>
            No Study Guides Found
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            Generate a study guide first, then come back to quiz by voice.
          </Typography>
          <Button
            variant="contained"
            onClick={() => navigate("/study-guide")}
            startIcon={<PlayArrowIcon />}
          >
            Go to Study Guides
          </Button>
        </Paper>
      </Container>
    );
  }

  return (
    <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
      {/* Header */}
      <Stack
        direction={{ xs: "column", sm: "row" }}
        justifyContent="space-between"
        alignItems={{ xs: "flex-start", sm: "center" }}
        spacing={2}
        sx={{ mb: 3 }}
      >
        <Box>
          <Typography variant="h1" gutterBottom sx={{ fontSize: { xs: "1.8rem", sm: "2.4rem" } }}>
            Voice Coach
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Practice out loud with real-time spoken guidance and oral quizzes.
          </Typography>
        </Box>

        {/* Status indicator strip */}
        <Chip
          label={`Voice sessions left today: ${remainingToday}`}
          color={remainingToday > 0 ? "primary" : "default"}
          variant="outlined"
          sx={{ fontWeight: "bold" }}
        />
      </Stack>

      {!isEnabled && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          Voice mode is turned off right now.
        </Alert>
      )}

      {isEnabled && remainingToday === 0 && (
        <Alert severity="info" sx={{ mb: 3 }}>
          You've used today's voice sessions on this device. Come back tomorrow.
        </Alert>
      )}

      {/* Guide selection if multiple guides exist */}
      {savedGuides.length > 1 && state === "idle" && (
        <FormControl fullWidth sx={{ mb: 3 }}>
          <InputLabel id="study-guide-select-label">Select Study Guide</InputLabel>
          <Select
            labelId="study-guide-select-label"
            value={selectedGuideId}
            label="Select Study Guide"
            onChange={(e) => setSelectedGuideId(e.target.value)}
          >
            {savedGuides.map((guide) => (
              <MenuItem key={guide.id} value={guide.id}>
                {guide.displayName || guide.studyGuide?.title}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      )}

      {/* Main interaction Card */}
      <Paper variant="outlined" sx={{ p: { xs: 2, sm: 4 }, mb: 3 }}>
        {/* State: Idle / Ready to start */}
        {state === "idle" && (
          <Box sx={{ textAlign: "center", py: 4 }}>
            <Typography variant="h6" gutterBottom>
              Study Guide: <strong>{activeStudyGuide?.title}</strong>
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 4, maxWidth: 600, mx: "auto" }}>
              {activeStudyGuide?.summary}
            </Typography>

            <Button
              variant="contained"
              size="large"
              color="primary"
              startIcon={<RecordVoiceOverIcon />}
              onClick={start}
              disabled={!canStartSession}
              sx={{ px: 4, py: 1.8, fontSize: "1.2rem", fontWeight: "bold" }}
            >
              Start Voice Quiz
            </Button>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 2, maxWidth: 480, mx: "auto" }}>
              The coach will speak right away to introduce the quiz and ask Question 1 out loud. Hold the microphone button to reply.
            </Typography>
          </Box>
        )}

        {/* State: Connecting */}
        {state === "connecting" && (
          <Box sx={{ textAlign: "center", py: 6 }}>
            <CircularProgress size={48} />
            <Typography variant="h6" sx={{ mt: 2 }}>
              Connecting to Voice Coach…
            </Typography>
          </Box>
        )}

        {/* State: Active session (ready or talking) */}
        {(state === "ready" || state === "talking") && (
          <Box>
            <VoiceControls
              state={state}
              secondsLeft={secondsLeft}
              onPressTalk={pressTalk}
              onReleaseTalk={releaseTalk}
              onEndSession={end}
            />

            <Divider sx={{ my: 3 }} />

            <VoiceScorePanel
              score={score}
              answers={answers}
              quizSummary={quizSummary}
            />

            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              Live Transcript
            </Typography>
            <VoiceTranscript transcript={transcript} />
          </Box>
        )}

        {/* State: Ended */}
        {state === "ended" && (
          <Box sx={{ py: 2 }}>
            <Alert severity="success" sx={{ mb: 3 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: "bold" }}>
                {endedReasonText}
              </Typography>
            </Alert>

            <VoiceScorePanel
              score={score}
              answers={answers}
              quizSummary={quizSummary}
            />

            <Typography variant="subtitle2" sx={{ mb: 1, mt: 2 }}>
              Session Transcript
            </Typography>
            <VoiceTranscript transcript={transcript} />

            <Stack direction="row" spacing={2} sx={{ mt: 3 }}>
              {canStartSession && (
                <Button
                  variant="contained"
                  startIcon={<RefreshIcon />}
                  onClick={start}
                >
                  Start Another Session
                </Button>
              )}
              <Button
                variant="outlined"
                startIcon={<ArrowBackIcon />}
                onClick={() => navigate("/study-guide")}
              >
                Back to Study Guides
              </Button>
            </Stack>
          </Box>
        )}

        {/* State: Error */}
        {state === "error" && (
          <Box sx={{ textAlign: "center", py: 4 }}>
            <Alert severity="error" sx={{ mb: 3, textAlign: "left" }}>
              {error?.message || "An unexpected error occurred."}
            </Alert>
            <Button
              variant="contained"
              startIcon={<RefreshIcon />}
              onClick={refreshStatus}
            >
              Try Again
            </Button>
          </Box>
        )}
      </Paper>
    </Container>
  );
}

export default VoicePage;
