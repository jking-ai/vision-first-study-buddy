import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles/global.css";

// TODO: Add React Router BrowserRouter wrapper
// TODO: Add error boundary for top-level error handling

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
