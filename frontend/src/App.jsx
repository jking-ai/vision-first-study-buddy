import React, { useState, useMemo, useEffect } from "react";
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

const STORAGE_KEY = "colorMode";
const DARK_QUERY = "(prefers-color-scheme: dark)";

function getSystemMode() {
  if (typeof window === "undefined" || !window.matchMedia) return "light";
  return window.matchMedia(DARK_QUERY).matches ? "dark" : "light";
}

function getStoredMode() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored === "light" || stored === "dark" ? stored : null;
  } catch {
    return null;
  }
}

function App() {
  // Explicit user choice wins; otherwise follow the OS preference live.
  const [storedMode, setStoredMode] = useState(getStoredMode);
  const [systemMode, setSystemMode] = useState(getSystemMode);
  const mode = storedMode || systemMode;

  useEffect(() => {
    if (!window.matchMedia) return undefined;
    const mql = window.matchMedia(DARK_QUERY);
    const onChange = (e) => setSystemMode(e.matches ? "dark" : "light");
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, []);

  const toggleColorMode = () => {
    const next = mode === "light" ? "dark" : "light";
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Storage unavailable (private mode); the in-memory choice still applies.
    }
    setStoredMode(next);
  };

  const theme = useMemo(() => createAppTheme(mode), [mode]);

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
          <TopNav mode={mode} toggleColorMode={toggleColorMode} />
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
