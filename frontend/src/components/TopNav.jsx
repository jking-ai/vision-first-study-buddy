import React, { useState } from "react";
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  IconButton,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Box,
} from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import Brightness4Icon from "@mui/icons-material/Brightness4";
import Brightness7Icon from "@mui/icons-material/Brightness7";
import { useNavigate, useLocation } from "react-router-dom";

const NAV_ITEMS = [
  { label: "Home", path: "/" },
  { label: "Materials", path: "/materials" },
  { label: "Study Guide", path: "/study-guide" },
  { label: "Quiz", path: "/quiz" },
  { label: "Voice Coach", path: "/voice" },
];

function TopNav({ mode, toggleColorMode }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [drawerOpen, setDrawerOpen] = useState(false);

  const handleNavigate = (path) => {
    navigate(path);
    setDrawerOpen(false);
  };

  return (
    <>
      <AppBar position="sticky">
        <Toolbar>
          {/* Mobile hamburger */}
          <IconButton
            color="inherit"
            edge="start"
            onClick={() => setDrawerOpen(true)}
            sx={{ mr: 1, display: { sm: "none" } }}
            aria-label="open navigation menu"
          >
            <MenuIcon />
          </IconButton>

          {/* App title */}
          <Typography
            variant="h6"
            component="div"
            sx={{ flexGrow: { xs: 1, sm: 0 }, mr: 3, cursor: "pointer" }}
            onClick={() => handleNavigate("/")}
          >
            Study Buddy
          </Typography>

          {/* Desktop nav */}
          <Box sx={{ display: { xs: "none", sm: "flex" }, flexGrow: 1, gap: 1 }}>
            {NAV_ITEMS.map((item) => (
              <Button
                key={item.path}
                color="inherit"
                onClick={() => handleNavigate(item.path)}
                sx={{
                  fontWeight: location.pathname === item.path ? 700 : 400,
                  textDecoration:
                    location.pathname === item.path ? "underline" : "none",
                }}
              >
                {item.label}
              </Button>
            ))}
          </Box>

          {/* Dark mode toggle */}
          <IconButton
            color="inherit"
            onClick={toggleColorMode}
            aria-label="toggle dark mode"
          >
            {mode === "dark" ? <Brightness7Icon /> : <Brightness4Icon />}
          </IconButton>
        </Toolbar>
      </AppBar>

      {/* Mobile drawer */}
      <Drawer
        anchor="left"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      >
        <Box sx={{ width: 220 }} role="presentation">
          <List>
            {NAV_ITEMS.map((item) => (
              <ListItem key={item.path} disablePadding>
                <ListItemButton
                  selected={location.pathname === item.path}
                  onClick={() => handleNavigate(item.path)}
                >
                  <ListItemText primary={item.label} />
                </ListItemButton>
              </ListItem>
            ))}
          </List>
        </Box>
      </Drawer>
    </>
  );
}

export default TopNav;
