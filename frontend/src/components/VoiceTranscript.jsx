import React, { useEffect, useRef } from "react";
import { Paper, Typography, Box, Stack, Avatar } from "@mui/material";
import PersonIcon from "@mui/icons-material/Person";
import SmartToyIcon from "@mui/icons-material/SmartToy";

export function VoiceTranscript({ transcript = [] }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcript]);

  if (!transcript || transcript.length === 0) {
    return (
      <Paper
        variant="outlined"
        sx={{
          p: 3,
          minHeight: 180,
          maxHeight: 320,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: (theme) =>
            theme.palette.mode === "dark" ? "rgba(255, 255, 255, 0.02)" : "rgba(0, 0, 0, 0.01)",
        }}
      >
        <Typography variant="body2" color="text.secondary" fontStyle="italic">
          Conversation transcript will appear here once the session begins...
        </Typography>
      </Paper>
    );
  }

  return (
    <Paper
      variant="outlined"
      sx={{
        p: 2,
        minHeight: 180,
        maxHeight: 320,
        overflowY: "auto",
        backgroundColor: (theme) =>
          theme.palette.mode === "dark" ? "rgba(255, 255, 255, 0.02)" : "rgba(0, 0, 0, 0.01)",
      }}
    >
      <Stack spacing={2}>
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
                maxWidth: "85%",
              }}
            >
              {!isUser && (
                <Avatar
                  sx={{
                    width: 28,
                    height: 28,
                    bgcolor: "primary.main",
                  }}
                >
                  <SmartToyIcon sx={{ fontSize: 16 }} />
                </Avatar>
              )}

              <Box
                sx={{
                  p: 1.5,
                  borderRadius: 2,
                  bgcolor: isUser
                    ? "primary.main"
                    : (theme) =>
                        theme.palette.mode === "dark"
                          ? "background.paper"
                          : "grey.100",
                  color: isUser ? "primary.contrastText" : "text.primary",
                  boxShadow: 1,
                }}
              >
                <Typography
                  variant="caption"
                  sx={{
                    fontWeight: "bold",
                    display: "block",
                    mb: 0.5,
                    opacity: isUser ? 0.9 : 0.7,
                  }}
                >
                  {isUser ? "You" : "Coach"}
                </Typography>
                <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
                  {entry.text}
                </Typography>
              </Box>

              {isUser && (
                <Avatar
                  sx={{
                    width: 28,
                    height: 28,
                    bgcolor: "secondary.main",
                  }}
                >
                  <PersonIcon sx={{ fontSize: 16 }} />
                </Avatar>
              )}
            </Stack>
          );
        })}
        <div ref={bottomRef} />
      </Stack>
    </Paper>
  );
}

export default VoiceTranscript;
