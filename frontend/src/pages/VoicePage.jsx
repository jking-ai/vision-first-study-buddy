import React, { useState, useEffect, useMemo, useRef } from "react";
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
} from "@mui/material";
import RecordVoiceOverIcon from "@mui/icons-material/RecordVoiceOver";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import RefreshIcon from "@mui/icons-material/Refresh";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import GraphicEqIcon from "@mui/icons-material/GraphicEq";

import { useVoiceSession } from "../hooks/useVoiceSession";
import { getSavedStudyGuides } from "../utils/studyGuideStorage";
import VoiceControls, { VOICE_DOCK_HEIGHT } from "../components/VoiceControls";
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
    inputLocked,
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
  const isLive = state === "ready" || state === "talking";
  const resultsRef = useRef(null);

  // The live view leaves the page scrolled to the last message; bring the
  // results into view when the session ends.
  useEffect(() => {
    if (state === "ended") {
      window.scrollTo({ top: 0, behavior: "auto" });
    }
  }, [state]);

  const scrollToResults = () => {
    resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const endedReasonText = useMemo(() => {
    switch (endedReason) {
      case "quiz_complete":
        return "Quiz complete!";
      case "max_duration":
        return "Time's up";
      case "idle_timeout":
        return "Session ended after inactivity";
      case "upstream_closed":
        return "Your tutor disconnected";
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
            Generate a study guide first, then come back to talk it out with your tutor.
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

  // Live session: compact header, conversation in page flow, controls docked
  // to the bottom of the viewport (see VoiceControls).
  if (isLive) {
    return (
      <>
        <Container
          maxWidth="md"
          sx={{ mt: 3, pb: `${VOICE_DOCK_HEIGHT + 24}px` }}
        >
          <Stack
            direction="row"
            justifyContent="space-between"
            alignItems="center"
            spacing={2}
            sx={{ mb: 2 }}
          >
            <Box sx={{ minWidth: 0 }}>
              <Typography variant="h2" component="h1" noWrap>
                Talking Tutor
              </Typography>
              <Typography variant="body2" color="text.secondary" noWrap>
                {activeStudyGuide?.title}
              </Typography>
            </Box>
            <Chip
              icon={<GraphicEqIcon />}
              label={inputLocked ? "Wrapping up" : state === "talking" ? "Listening" : "Live"}
              color={inputLocked ? "warning" : state === "talking" ? "secondary" : "success"}
              variant="outlined"
              sx={{ fontWeight: 600, flexShrink: 0 }}
            />
          </Stack>

          {(score || answers.length > 0 || quizSummary) && (
            <Box sx={{ mb: 2 }}>
              <VoiceScorePanel
                score={score}
                answers={answers}
                quizSummary={quizSummary}
                collapsible
              />
            </Box>
          )}

          <VoiceTranscript transcript={transcript} autoScroll />
        </Container>

        <VoiceControls
          state={state}
          secondsLeft={secondsLeft}
          disabled={inputLocked}
          onPressTalk={pressTalk}
          onReleaseTalk={releaseTalk}
          onEndSession={end}
        />
      </>
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
            Talking Tutor
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Say your answers out loud. Your tutor asks questions from your study guide and replies with spoken feedback.
          </Typography>
        </Box>

        {/* Status indicator strip */}
        <Chip
          label={`Sessions left today: ${remainingToday}`}
          color={remainingToday > 0 ? "primary" : "default"}
          variant="outlined"
          sx={{ fontWeight: 600, flexShrink: 0 }}
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
              sx={{ px: 4, py: 1.8, fontSize: "1.2rem" }}
            >
              Start Talking
            </Button>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 2, maxWidth: 480, mx: "auto" }}>
              Your tutor will introduce the quiz and ask Question 1 out loud. Hold the microphone button to reply.
            </Typography>
          </Box>
        )}

        {/* State: Connecting */}
        {state === "connecting" && (
          <Box sx={{ textAlign: "center", py: 6 }}>
            <CircularProgress size={48} />
            <Typography variant="h6" sx={{ mt: 2 }}>
              Connecting to your tutor…
            </Typography>
          </Box>
        )}

        {/* State: Ended */}
        {state === "ended" && (
          <Box>
            <Alert
              severity="success"
              sx={{ mb: 3, alignItems: "center" }}
              action={
                (score || answers.length > 0 || quizSummary) && (
                  <Button color="inherit" size="small" onClick={scrollToResults}>
                    View results
                  </Button>
                )
              }
            >
              <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                {endedReasonText}
              </Typography>
              {score && (
                <Typography variant="body2">
                  You scored {score.correct} of {score.total}.
                </Typography>
              )}
            </Alert>

            <Box ref={resultsRef} sx={{ scrollMarginTop: 80 }}>
              <VoiceScorePanel
                score={score}
                answers={answers}
                quizSummary={quizSummary}
              />
            </Box>

            <Typography variant="subtitle2" sx={{ mb: 1.5, mt: 3 }}>
              Session transcript
            </Typography>
            <VoiceTranscript transcript={transcript} />

            <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ mt: 3 }}>
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
