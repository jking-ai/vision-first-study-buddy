import React, { useRef, useLayoutEffect } from "react";
import { Paper, Typography, Box, Stack, Avatar } from "@mui/material";
import PersonIcon from "@mui/icons-material/Person";
import SmartToyIcon from "@mui/icons-material/SmartToy";

// How close to the bottom (px) the reader must be for auto-scroll to stay engaged.
const STICKY_THRESHOLD = 160;

/**
 * Conversation transcript rendered in page flow.
 *
 * With `autoScroll`, the page follows the newest message as it streams in,
 * but stops following if the reader has scrolled up to re-read something.
 * Stickiness is measured against the page height recorded after the previous
 * update, so it needs no scroll listener and works even while frames are
 * throttled.
 */
export function VoiceTranscript({ transcript = [], autoScroll = false }) {
  const lastScrollHeight = useRef(null);

  useLayoutEffect(() => {
    if (!autoScroll) {
      lastScrollHeight.current = null;
      return;
    }
    const doc = document.documentElement;
    const previousHeight = lastScrollHeight.current ?? doc.scrollHeight;
    const distanceFromBottom = previousHeight - (window.innerHeight + window.scrollY);
    const shouldStick = distanceFromBottom < STICKY_THRESHOLD;

    if (shouldStick) {
      window.scrollTo({ top: doc.scrollHeight, behavior: "auto" });
    }
    lastScrollHeight.current = doc.scrollHeight;
  }, [transcript, autoScroll]);

  if (!transcript || transcript.length === 0) {
    return (
      <Paper
        variant="outlined"
        sx={{
          p: 3,
          minHeight: 160,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          bgcolor: "action.hover",
        }}
      >
        <Typography variant="body2" color="text.secondary" fontStyle="italic" align="center">
          The conversation will appear here once the coach starts speaking.
        </Typography>
      </Paper>
    );
  }

  return (
    <Stack spacing={2} aria-live="polite" aria-label="Conversation transcript">
      {transcript.map((entry, idx) => {
        const isUser = entry.role === "user";
        return (
          <Stack
            key={idx}
            direction="row"
            spacing={1.5}
            alignItems="flex-start"
            sx={{
              alignSelf: isUser ? "flex-end" : "flex-start",
              maxWidth: { xs: "92%", sm: "80%" },
            }}
          >
            {!isUser && (
              <Avatar sx={{ width: 28, height: 28, bgcolor: "primary.main", color: "primary.contrastText" }}>
                <SmartToyIcon sx={{ fontSize: 16 }} />
              </Avatar>
            )}

            <Box
              sx={{
                px: 1.75,
                py: 1.25,
                borderRadius: 2.5,
                borderTopLeftRadius: isUser ? 20 : 4,
                borderTopRightRadius: isUser ? 4 : 20,
                bgcolor: isUser ? "primary.main" : "background.paper",
                color: isUser ? "primary.contrastText" : "text.primary",
                border: isUser ? 0 : 1,
                borderColor: "divider",
              }}
            >
              <Typography
                variant="caption"
                sx={{ fontWeight: 600, display: "block", mb: 0.25, opacity: 0.8 }}
              >
                {isUser ? "You" : "Coach"}
              </Typography>
              <Typography variant="body2" sx={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>
                {entry.text}
                {!entry.completed && (
                  <Box
                    component="span"
                    aria-hidden
                    sx={{
                      display: "inline-block",
                      width: 6,
                      height: 12,
                      ml: 0.5,
                      borderRadius: 1,
                      bgcolor: "currentColor",
                      opacity: 0.6,
                      verticalAlign: "-1px",
                      animation: "vfsb-blink 1s steps(2, start) infinite",
                      "@keyframes vfsb-blink": { to: { visibility: "hidden" } },
                    }}
                  />
                )}
              </Typography>
            </Box>

            {isUser && (
              <Avatar sx={{ width: 28, height: 28, bgcolor: "secondary.main", color: "secondary.contrastText" }}>
                <PersonIcon sx={{ fontSize: 16 }} />
              </Avatar>
            )}
          </Stack>
        );
      })}
    </Stack>
  );
}

export default VoiceTranscript;
