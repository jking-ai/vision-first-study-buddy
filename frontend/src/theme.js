import { createTheme } from "@mui/material/styles";

/**
 * Create a MUI theme for Vision-First Study Buddy.
 *
 * @param {"light"|"dark"} mode - Color mode
 * @returns {import("@mui/material").Theme}
 */
export function createAppTheme(mode) {
  const isDark = mode === "dark";
  return createTheme({
    palette: {
      mode,
      primary: {
        main: isDark ? "#64b5f6" : "#1976d2",
      },
      secondary: {
        main: isDark ? "#81c784" : "#388e3c",
      },
      background: isDark
        ? { default: "#121212", paper: "#1e1e1e" }
        : { default: "#f6f8fb", paper: "#ffffff" },
    },
    shape: {
      borderRadius: 10,
    },
    typography: {
      fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
      h1: { fontSize: "2rem", fontWeight: 600 },
      h2: { fontSize: "1.5rem", fontWeight: 600 },
      body1: { fontSize: "1rem", lineHeight: 1.6 },
    },
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          html: { colorScheme: mode },
          body: { backgroundColor: isDark ? "#121212" : "#f6f8fb" },
        },
      },
      MuiAppBar: {
        styleOverrides: {
          root: isDark
            ? {
                // A flat dark surface with a hairline, instead of MUI's
                // elevation-tinted grey, so it matches the cards below it.
                backgroundColor: "#1e1e1e",
                backgroundImage: "none",
                borderBottom: "1px solid rgba(255, 255, 255, 0.12)",
                boxShadow: "none",
              }
            : {},
        },
      },
      MuiCard: {
        defaultProps: {
          elevation: 0,
        },
        styleOverrides: {
          root: ({ theme }) => ({
            border: `1px solid ${theme.palette.divider}`,
          }),
        },
      },
      MuiPaper: {
        styleOverrides: {
          root: {
            backgroundImage: "none",
          },
        },
      },
      MuiButton: {
        styleOverrides: {
          root: {
            borderRadius: 8,
            textTransform: "none",
            fontWeight: 600,
          },
        },
      },
      MuiTab: {
        styleOverrides: {
          root: {
            textTransform: "none",
            fontWeight: 600,
          },
        },
      },
      MuiTableCell: {
        styleOverrides: {
          head: {
            fontWeight: 600,
          },
        },
      },
    },
  });
}

export default createAppTheme;
