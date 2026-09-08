import React, { useMemo } from "react";
import { ThemeProvider, CssBaseline, Box } from "@mui/material";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { createAppTheme } from "./theme";
import TopNav from "./components/TopNav";
import Footer from "./components/Footer";
import HomePage from "./pages/HomePage";
import MaterialsPage from "./pages/MaterialsPage";
import StudyGuidePage from "./pages/StudyGuidePage";
import QuizPage from "./pages/QuizPage";
import VoicePage from "./pages/VoicePage";

function App() {
  const theme = useMemo(() => createAppTheme(), []);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <Box
          sx={{
            minHeight: "100dvh",
            display: "flex",
            flexDirection: "column",
            bgcolor: "background.default",
          }}
        >
          <TopNav />
          <Box
            component="main"
            sx={{ flex: 1, pb: "calc(var(--vfsb-footer-height) + 16px)" }}
          >
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/materials" element={<MaterialsPage />} />
              <Route path="/study-guide" element={<StudyGuidePage />} />
              <Route path="/quiz" element={<QuizPage />} />
              <Route path="/voice" element={<VoicePage />} />
            </Routes>
          </Box>
          <Footer />
        </Box>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
