import { createTheme } from "@mui/material/styles";

/**
 * Create the MUI theme for Vision-First Study Buddy.
 *
 * The app is light-only. index.html also opts out of the Dark Reader
 * extension, whose fallback stylesheet paints every element the same grey.
 *
 * @returns {import("@mui/material").Theme}
 */
export function createAppTheme() {
  return createTheme({
    palette: {
      mode: "light",
      primary: {
        main: "#1976d2",
      },
      secondary: {
        main: "#388e3c",
      },
      background: { default: "#f6f8fb", paper: "#ffffff" },
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
          html: { colorScheme: "light" },
          body: { backgroundColor: "#f6f8fb" },
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
