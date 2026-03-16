import React from "react";
import { Container, Typography } from "@mui/material";

/**
 * MaterialsPage -- material management and selection view.
 *
 * TODO (Phase 4+): MaterialUpload component, CameraCapture toggle,
 * MaterialList with selection mode, action buttons for study guide / quiz.
 */
function MaterialsPage() {
  return (
    <Container maxWidth="md" sx={{ mt: 4 }}>
      <Typography variant="h1" gutterBottom>
        My Materials
      </Typography>
      <Typography variant="body1" color="text.secondary">
        Upload and manage your study materials here.
      </Typography>
    </Container>
  );
}

export default MaterialsPage;
