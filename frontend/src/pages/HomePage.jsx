import React from "react";
import { Container, Typography, Box } from "@mui/material";

/**
 * HomePage -- landing page with upload call-to-action and feature overview.
 *
 * TODO (Phase 4+): Implement hero section, "How it works" cards,
 * MaterialUpload component, camera capture button, recent materials list.
 */
function HomePage() {
  return (
    <Container maxWidth="md" sx={{ mt: 4 }}>
      <Box>
        <Typography variant="h1" gutterBottom>
          Vision-First Study Buddy
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Upload your notes, whiteboard photos, PDFs, and epubs — then generate
          personalized study guides and quizzes powered by Gemini 1.5 Flash.
        </Typography>
      </Box>
    </Container>
  );
}

export default HomePage;
