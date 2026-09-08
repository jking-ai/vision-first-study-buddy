import React, { useEffect, useCallback } from "react";
import { Box, Button, Typography, Stack, Chip } from "@mui/material";
import MicIcon from "@mui/icons-material/Mic";
import StopCircleIcon from "@mui/icons-material/StopCircle";
import TimerIcon from "@mui/icons-material/Timer";

function formatSeconds(seconds) {
  if (seconds === null || seconds === undefined) return "0:00";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s < 10 ? "0" : ""}${s}`;
}

export function VoiceControls({
  state,
  secondsLeft,
  onPressTalk,
  onReleaseTalk,
  onEndSession,
  disabled = false,
}) {
  const isTalking = state === "talking";

  const handleKeyDown = useCallback(
    (e) => {
      if (e.code === "Space" && !disabled && (state === "ready" || state === "talking")) {
        // Prevent page scroll
        e.preventDefault();
        onPressTalk();
      }
    },
    [disabled, state, onPressTalk]
  );

  const handleKeyUp = useCallback(
    (e) => {
      if (e.code === "Space" && !disabled && (state === "ready" || state === "talking")) {
        e.preventDefault();
        onReleaseTalk();
      }
    },
    [disabled, state, onReleaseTalk]
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
    };
  }, [handleKeyDown, handleKeyUp]);

  return (
    <Box sx={{ textAlign: "center", py: 2 }}>
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        sx={{ mb: 3 }}
      >
        <Chip
          icon={<TimerIcon />}
          label={formatSeconds(secondsLeft)}
          color={secondsLeft !== null && secondsLeft < 30 ? "error" : "primary"}
          variant="outlined"
          sx={{ fontWeight: "bold", fontSize: "1rem", px: 1 }}
        />
        <Button
          variant="outlined"
          color="error"
          startIcon={<StopCircleIcon />}
          onClick={onEndSession}
          size="small"
        >
          End Session
        </Button>
      </Stack>

      {/* Push-to-talk button */}
      <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", my: 2 }}>
        <Button
          variant="contained"
          color={isTalking ? "secondary" : "primary"}
          disabled={disabled}
          onPointerDown={onPressTalk}
          onPointerUp={onReleaseTalk}
          onPointerCancel={onReleaseTalk}
          onPointerLeave={onReleaseTalk}
          sx={{
            width: 140,
            height: 140,
            borderRadius: "50%",
            boxShadow: isTalking
              ? "0 0 24px rgba(255, 64, 129, 0.6)"
              : "0 4px 14px rgba(0, 0, 0, 0.2)",
            transform: isTalking ? "scale(0.96)" : "scale(1)",
            transition: "all 0.15s ease",
            display: "flex",
            flexDirection: "column",
            gap: 1,
            userSelect: "none",
            touchAction: "none",
          }}
        >
          <MicIcon sx={{ fontSize: 48 }} />
          <Typography variant="button" sx={{ fontSize: "0.85rem", fontWeight: "bold" }}>
            {isTalking ? "Listening..." : "Hold to Answer"}
          </Typography>
        </Button>
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1.5 }}>
          Hold button or press Space to speak your answer • Release when done
        </Typography>
      </Box>
    </Box>
  );
}

export default VoiceControls;
