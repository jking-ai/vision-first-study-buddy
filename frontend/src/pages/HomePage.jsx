import React from "react";
import { useNavigate } from "react-router-dom";
import {
  Container,
  Typography,
  Box,
  Button,
  Card,
  CardContent,
  Stack,
} from "@mui/material";
import Grid from "@mui/material/Grid2";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import AutoStoriesIcon from "@mui/icons-material/AutoStories";
import QuizIcon from "@mui/icons-material/Quiz";
import RecordVoiceOverIcon from "@mui/icons-material/RecordVoiceOver";

const steps = [
  {
    icon: <CloudUploadIcon sx={{ fontSize: 48 }} color="primary" />,
    title: "Upload Materials",
    description:
      "Snap photos of notes, upload PDFs, or add ebook chapters. Supports JPEG, PNG, WebP, PDF, and EPUB.",
  },
  {
    icon: <AutoStoriesIcon sx={{ fontSize: 48 }} color="primary" />,
    title: "Generate Study Guide",
    description:
      "AI analyzes your materials and creates a structured study guide with key terms and summaries.",
  },
  {
    icon: <QuizIcon sx={{ fontSize: 48 }} color="primary" />,
    title: "Take a Quiz",
    description:
      "Test your knowledge with auto-generated quizzes. Get instant feedback and explanations.",
  },
  {
    icon: <RecordVoiceOverIcon sx={{ fontSize: 48 }} color="primary" />,
    title: "Talking Tutor",
    description:
      "Talk it out. Your tutor asks questions from your study guide, listens to your answers, and replies out loud.",
  },
];

function HomePage() {
  const navigate = useNavigate();

  return (
    <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
      {/* Hero */}
      <Box sx={{ textAlign: "center", py: 4 }}>
        <Typography variant="h1" gutterBottom>
          Vision-First Study Buddy
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          Turn handwritten notes, whiteboard photos, PDFs, and ebooks into personalized study guides and interactive quizzes.
        </Typography>
        <Button
          variant="contained"
          size="large"
          startIcon={<CloudUploadIcon />}
          onClick={() => navigate("/materials")}
        >
          Upload Materials
        </Button>
      </Box>

      {/* How it works */}
      <Typography variant="h2" sx={{ textAlign: "center", mt: 4, mb: 3 }}>
        How It Works
      </Typography>
      <Grid container spacing={3}>
        {steps.map((step, i) => (
          <Grid key={i} size={{ xs: 12, sm: 6 }}>
            <Card sx={{ textAlign: "center", height: "100%", p: 2 }}>
              <CardContent>
                {step.icon}
                <Typography variant="h6" sx={{ mt: 1, mb: 1 }}>
                  {step.title}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {step.description}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Quick links */}
      <Stack direction="row" spacing={2} justifyContent="center" sx={{ mt: 4 }}>
        <Button variant="outlined" startIcon={<AutoStoriesIcon />} onClick={() => navigate("/study-guide")}>
          Study Guide
        </Button>
        <Button variant="outlined" startIcon={<QuizIcon />} onClick={() => navigate("/quiz")}>
          Quiz
        </Button>
      </Stack>
    </Container>
  );
}

export default HomePage;
