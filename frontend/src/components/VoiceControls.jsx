import React, { useEffect, useCallback } from "react";
import { Box, Button, Typography, Stack, Chip, Container } from "@mui/material";
import MicIcon from "@mui/icons-material/Mic";
import StopCircleIcon from "@mui/icons-material/StopCircle";
import TimerIcon from "@mui/icons-material/Timer";

/** Height of the fixed push-to-talk dock, in px. Pages add this as bottom padding. */
export const VOICE_DOCK_HEIGHT = 104;

function formatSeconds(seconds) {
  if (seconds === null || seconds === undefined) return "0:00";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s < 10 ? "0" : ""}${s}`;
}

/**
 * Push-to-talk controls, docked to the bottom of the viewport (above the
 * status footer) so they stay put while the conversation scrolls behind them.
 */
export function VoiceControls({
  state,
  secondsLeft,
  onPressTalk,
  onReleaseTalk,
  onEndSession,
  disabled = false,
}) {
  const isTalking = state === "talking";
  const isActive = state === "ready" || state === "talking";

  const handleKeyDown = useCallback(
    (e) => {
      if (e.code === "Space" && !e.repeat && !disabled && isActive) {
        // Prevent page scroll
        e.preventDefault();
        onPressTalk();
      }
    },
    [disabled, isActive, onPressTalk]
  );

  const handleKeyUp = useCallback(
    (e) => {
      if (e.code === "Space" && !disabled && isActive) {
        e.preventDefault();
        onReleaseTalk();
      }
    },
    [disabled, isActive, onReleaseTalk]
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
    };
  }, [handleKeyDown, handleKeyUp]);

  const timerUrgent = secondsLeft !== null && secondsLeft < 30;

  return (
    <Box
      component="section"
      aria-label="Voice controls"
      sx={{
        position: "fixed",
        left: 0,
        right: 0,
        bottom: "var(--vfsb-footer-height)",
        height: VOICE_DOCK_HEIGHT,
        zIndex: (theme) => theme.zIndex.appBar,
        bgcolor: "background.paper",
        borderTop: 1,
        borderColor: "divider",
        boxShadow: "0 -8px 24px rgba(15, 23, 42, 0.08)",
      }}
    >
      <Container maxWidth="md" sx={{ height: "100%" }}>
        <Stack
          direction="row"
          alignItems="center"
          justifyContent="space-between"
          spacing={{ xs: 1, sm: 2 }}
          sx={{ height: "100%" }}
        >
          {/* Countdown */}
          <Chip
            icon={<TimerIcon />}
            label={formatSeconds(secondsLeft)}
            color={timerUrgent ? "error" : "default"}
            variant="outlined"
            sx={{
              fontWeight: 600,
              fontVariantNumeric: "tabular-nums",
              minWidth: 84,
            }}
            aria-label={`${formatSeconds(secondsLeft)} remaining`}
          />

          {/* Push-to-talk */}
          <Stack direction="row" alignItems="center" spacing={1.5} sx={{ minWidth: 0 }}>
            <Button
              variant="contained"
              color={isTalking ? "secondary" : "primary"}
              disabled={disabled || !isActive}
              onPointerDown={(e) => {
                e.preventDefault();
                onPressTalk();
              }}
              onPointerUp={onReleaseTalk}
              onPointerCancel={onReleaseTalk}
              onPointerLeave={onReleaseTalk}
              onContextMenu={(e) => e.preventDefault()}
              aria-pressed={isTalking}
              aria-label={isTalking ? "Listening, release to finish" : "Hold to answer"}
              sx={{
                width: 72,
                height: 72,
                minWidth: 72,
                borderRadius: "50%",
                flexShrink: 0,
                boxShadow: (theme) =>
                  isTalking
                    ? `0 0 0 8px ${theme.palette.secondary.main}33`
                    : theme.shadows[4],
                transform: isTalking ? "scale(0.94)" : "scale(1)",
                transition: "transform 0.15s ease, box-shadow 0.15s ease",
                userSelect: "none",
                touchAction: "none",
                WebkitTouchCallout: "none",
              }}
            >
              <MicIcon sx={{ fontSize: 34 }} />
            </Button>
            <Box sx={{ display: { xs: "none", sm: "block" } }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600, lineHeight: 1.3 }}>
                {isTalking ? "Listening…" : "Hold to answer"}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {isTalking ? "Release when you're done" : "Hold the button or press Space"}
              </Typography>
            </Box>
          </Stack>

          {/* End session */}
          <Button
            variant="outlined"
            color="error"
            startIcon={<StopCircleIcon />}
            onClick={onEndSession}
            size="small"
            sx={{ flexShrink: 0, minWidth: 84 }}
          >
            End
          </Button>
        </Stack>
      </Container>
    </Box>
  );
}

export default VoiceControls;
