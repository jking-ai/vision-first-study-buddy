import React, { useState, useEffect, useRef, useCallback } from "react";
import { Box, Typography } from "@mui/material";
import SpaIcon from "@mui/icons-material/Spa";
import apiClient from "../api/client";

const STATUS = {
  CHECKING: "checking",
  WARMING: "warming",
  ONLINE: "online",
  OFFLINE: "offline",
};

const statusConfig = {
  [STATUS.CHECKING]: { color: "text.disabled", ping: true, text: "Checking API..." },
  [STATUS.WARMING]: { color: "warning.main", ping: true, text: "API warming up..." },
  [STATUS.ONLINE]: { color: "success.main", ping: false, text: "API online" },
  [STATUS.OFFLINE]: { color: "error.main", ping: false, text: "API offline" },
};

function Footer() {
  const [status, setStatus] = useState(STATUS.CHECKING);
  const warmingTimer = useRef(null);

  const checkHealth = useCallback(async () => {
    setStatus(STATUS.CHECKING);

    warmingTimer.current = setTimeout(() => setStatus(STATUS.WARMING), 2000);

    try {
      const data = await apiClient.health();
      clearTimeout(warmingTimer.current);
      setStatus(data.status === "healthy" ? STATUS.ONLINE : STATUS.OFFLINE);
    } catch {
      clearTimeout(warmingTimer.current);
      setStatus(STATUS.OFFLINE);
    }
  }, []);

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 60000);
    return () => {
      clearInterval(interval);
      clearTimeout(warmingTimer.current);
    };
  }, [checkHealth]);

  const { color, ping, text } = statusConfig[status];

  return (
    <Box
      component="footer"
      sx={{
        position: "fixed",
        bottom: 0,
        left: 0,
        right: 0,
        height: "var(--vfsb-footer-height)",
        borderTop: 1,
        borderColor: "divider",
        bgcolor: "background.paper",
        zIndex: (theme) => theme.zIndex.appBar,
        px: 2,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 2,
      }}
    >
      {/* Inspirational quote */}
      <Typography
        variant="caption"
        color="text.secondary"
        noWrap
        sx={{ display: "flex", alignItems: "center", gap: 0.5, minWidth: 0 }}
      >
        <SpaIcon sx={{ fontSize: 14, color: "success.main", flexShrink: 0 }} />
        <Box component="span" sx={{ overflow: "hidden", textOverflow: "ellipsis" }}>
          Keep asking questions — that's how you grow.
        </Box>
      </Typography>

      {/* Status indicator */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexShrink: 0 }}>
        {/* Animated dot */}
        <Box sx={{ position: "relative", width: 10, height: 10 }}>
          {/* Ping ring */}
          {ping && (
            <Box
              sx={{
                position: "absolute",
                inset: 0,
                borderRadius: "50%",
                bgcolor: color,
                opacity: 0.6,
                animation: "ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite",
                "@keyframes ping": {
                  "0%": { transform: "scale(1)", opacity: 0.6 },
                  "75%, 100%": { transform: "scale(2.2)", opacity: 0 },
                },
              }}
            />
          )}
          {/* Solid dot */}
          <Box
            sx={{
              position: "relative",
              width: 10,
              height: 10,
              borderRadius: "50%",
              bgcolor: color,
            }}
          />
        </Box>
        <Typography variant="caption" color="text.secondary" noWrap>
          {text}
        </Typography>
      </Box>
    </Box>
  );
}

export default Footer;
