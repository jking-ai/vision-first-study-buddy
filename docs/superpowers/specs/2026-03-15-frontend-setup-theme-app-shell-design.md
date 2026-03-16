# Frontend Setup, Theme & App Shell — Design Spec

**Date:** 2026-03-15
**Issue:** jking-ai/vision-first-study-buddy#8
**Phase:** 3 — Frontend Foundation

---

## Overview

Implement the foundational React app shell for Vision-First Study Buddy: MUI theme (light/dark), React Router navigation, TopNav, error boundary, API client, and Vite proxy config. All stubs exist; this spec covers completing them.

---

## Architecture

### Dark Mode Strategy

Dark mode state lives in `App.jsx` using `useState` with `localStorage` persistence. `App` creates the MUI theme dynamically based on current mode via `useMemo`. A `toggleColorMode` callback is passed down to `TopNav` via props.

This avoids Context API complexity for a single toggle — props are clear and testable.

### Theme (`theme.js`)

Export a `createAppTheme(mode)` function (not a static theme object) so `App` can create a new theme whenever mode changes.

```
createAppTheme(mode) → MUI theme
  palette: primary #1976d2, secondary #388e3c
  typography: Roboto, h1 2rem, h2 1.5rem, body1 1rem/1.6
  component overrides: MuiCard elevation:2, MuiButton borderRadius:8
  breakpoints: default MUI (xs/sm/md/lg/xl)
```

### App Shell (`App.jsx`)

```
App
  ├── reads colorMode from localStorage (default: 'light')
  ├── creates theme via createAppTheme(mode)
  ├── ThemeProvider + CssBaseline
  └── BrowserRouter (moved from main.jsx — simpler, no extra wrapping)
      ├── TopNav (receives mode + toggleColorMode)
      └── Routes
          ├── / → HomePage
          ├── /materials → MaterialsPage
          ├── /study-guide → StudyGuidePage
          └── /quiz → QuizPage
```

### Entry Point (`main.jsx`)

Adds `ErrorBoundary` class component wrapping `App`. `BrowserRouter` moves into `App` so the router is co-located with routes.

### TopNav (`TopNav.jsx`)

MUI `AppBar` + `Toolbar`:
- Left: app title (Typography, links to `/`)
- Center/Right (desktop): `Button` links for Home, Materials, Study Guide, Quiz using `useNavigate`
- Right: `IconButton` for dark mode toggle (Brightness4 / Brightness7)
- Mobile (`xs`–`sm`): hamburger `IconButton` opens `Drawer` with nav list

### API Client (`api/client.js`)

`request(path, options)` implementation:
1. Build URL: `${API_BASE_URL}${API_PREFIX}${path}`
2. Default headers: `Content-Type: application/json` (omitted for FormData)
3. `fetch()` call
4. If `!response.ok`: parse error body, throw `Error(body.detail || body.message || response.statusText)`
5. On network failure: throw `Error("Network error — is the backend running?")`
6. Return `response.json()`

All 9 methods delegate to `request()`. `uploadMaterials` builds `FormData` and omits `Content-Type` header (browser sets multipart boundary automatically).

### Vite Proxy (`vite.config.js`)

```js
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
  }
}
```

### Page Shells

Each page gets a minimal MUI `Container` with a `Typography` heading and placeholder text. No functional implementation — that's future phases.

---

## Error Handling

- API client: server errors → parse `detail`/`message` from JSON body; network errors → friendly message
- Error boundary in `main.jsx`: catches render errors, shows fallback UI

---

## Files Modified

| File | Change |
|------|--------|
| `frontend/src/theme.js` | Implement `createAppTheme(mode)` |
| `frontend/src/main.jsx` | Add `ErrorBoundary`, wrap in `<ErrorBoundary>` |
| `frontend/src/App.jsx` | Full implementation: ThemeProvider, dark mode, BrowserRouter, routes |
| `frontend/src/components/TopNav.jsx` | AppBar, nav buttons, dark mode toggle, mobile drawer |
| `frontend/src/api/client.js` | Implement `request()` and all 9 API methods |
| `frontend/vite.config.js` | Enable `/api` proxy to `localhost:8000` |
| `frontend/src/pages/*.jsx` | MUI Container + placeholder heading per page |

---

## Assumptions

- `BrowserRouter` moves from `main.jsx` into `App.jsx` (co-location with routes is cleaner)
- Dark mode default is `'light'`; persisted in `localStorage` key `colorMode`
- `uploadMaterials` omits `Content-Type` so browser auto-sets multipart boundary
- Page shells are minimal placeholder only — full implementation is future phases
