import React from "react";
import { Container, Typography } from "@mui/material";

/**
 * StudyGuidePage -- study guide generation and display.
 *
 * TODO (Phase 4+): Material selection summary, focus topics input,
 * detail level selector, Generate button, loading state, StudyGuideView,
 * error state with retry. Uses useStudyGuide hook.
 */
function StudyGuidePage() {
  return (
    <Container maxWidth="md" sx={{ mt: 4 }}>
      <Typography variant="h1" gutterBottom>
        Study Guide
      </Typography>
      <Typography variant="body1" color="text.secondary">
        Select materials and generate a personalized study guide.
      </Typography>
    </Container>
  );
}

export default StudyGuidePage;
