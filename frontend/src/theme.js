import { createTheme } from "@mui/material/styles";

/**
 * Create a MUI theme for Vision-First Study Buddy.
 *
 * @param {"light"|"dark"} mode - Color mode
 * @returns {import("@mui/material").Theme}
 */
export function createAppTheme(mode) {
  return createTheme({
    palette: {
      mode,
      primary: {
        main: "#1976d2",
      },
      secondary: {
        main: "#388e3c",
      },
    },
    typography: {
      fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
      h1: { fontSize: "2rem", fontWeight: 600 },
      h2: { fontSize: "1.5rem", fontWeight: 600 },
      body1: { fontSize: "1rem", lineHeight: 1.6 },
    },
    components: {
      MuiCard: {
        defaultProps: {
          elevation: 2,
        },
      },
      MuiButton: {
        styleOverrides: {
          root: {
            borderRadius: 8,
          },
        },
      },
    },
  });
}

export default createAppTheme;
