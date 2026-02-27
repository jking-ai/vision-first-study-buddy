import React, { useState, useMemo } from "react";
import { ThemeProvider, CssBaseline, Box } from "@mui/material";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { createAppTheme } from "./theme";
import TopNav from "./components/TopNav";
import Footer from "./components/Footer";
import HomePage from "./pages/HomePage";
import MaterialsPage from "./pages/MaterialsPage";
import StudyGuidePage from "./pages/StudyGuidePage";
import QuizPage from "./pages/QuizPage";

function App() {
  const [mode, setMode] = useState(
    () => localStorage.getItem("colorMode") || "light"
  );

  const toggleColorMode = () => {
    setMode((prev) => {
      const next = prev === "light" ? "dark" : "light";
      localStorage.setItem("colorMode", next);
      return next;
    });
  };

  const theme = useMemo(() => createAppTheme(mode), [mode]);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <TopNav mode={mode} toggleColorMode={toggleColorMode} />
        <Box sx={{ pb: 5 }}>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/materials" element={<MaterialsPage />} />
            <Route path="/study-guide" element={<StudyGuidePage />} />
            <Route path="/quiz" element={<QuizPage />} />
          </Routes>
        </Box>
        <Footer />
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
