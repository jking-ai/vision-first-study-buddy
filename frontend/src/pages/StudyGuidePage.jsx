import React, { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import RecordVoiceOverIcon from "@mui/icons-material/RecordVoiceOver";
import {
  Container,
  Typography,
  TextField,
  Button,
  Alert,
  Box,
  CircularProgress,
  ToggleButton,
  ToggleButtonGroup,
  Divider,
  Card,
  CardContent,
  CardActions,
  Stack,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Snackbar,
} from "@mui/material";
import Grid from "@mui/material/Grid2";
import AutoStoriesIcon from "@mui/icons-material/AutoStories";
import SaveIcon from "@mui/icons-material/Save";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import VisibilityIcon from "@mui/icons-material/Visibility";
import StudyGuideView from "../components/StudyGuideView";
import MaterialList from "../components/MaterialList";
import useStudyGuide from "../hooks/useStudyGuide";
import useMaterials from "../hooks/useMaterials";

function StudyGuidePage() {
  const location = useLocation();
  const navigate = useNavigate();
  const passedIds = location.state?.selectedIds || [];

  const { materials, loading: materialsLoading } = useMaterials();
  const {
    generate,
    studyGuide,
    loading,
    error,
    reset,
    savedGuides,
    save,
    loadSaved,
    deleteSaved,
    renameSaved,
  } = useStudyGuide();

  const [selectedIds, setSelectedIds] = useState(passedIds);
  const [focusTopics, setFocusTopics] = useState("");
  const [detailLevel, setDetailLevel] = useState("standard");
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [saveName, setSaveName] = useState("");
  const [renameDialogOpen, setRenameDialogOpen] = useState(false);
  const [renameTarget, setRenameTarget] = useState(null);
  const [renameName, setRenameName] = useState("");
  const [viewingSaved, setViewingSaved] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const handleGenerate = () => {
    if (selectedIds.length === 0) return;
    const topics = focusTopics
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
    generate(selectedIds, topics, detailLevel);
    setViewingSaved(false);
  };

  const handleSave = () => {
    if (studyGuide) {
      setSaveName(studyGuide.title);
      setSaveDialogOpen(true);
    }
  };

  const handleConfirmSave = () => {
    save(studyGuide, saveName);
    setSaveDialogOpen(false);
    setSaveName("");
    setSaveSuccess(true);
    // Return to the main study guide view after a short delay
    setTimeout(() => {
      reset();
      setViewingSaved(false);
    }, 1500);
  };

  const handleViewSaved = (entry) => {
    loadSaved(entry);
    setViewingSaved(true);
  };

  const handleOpenRename = (entry) => {
    setRenameTarget(entry);
    setRenameName(entry.displayName);
    setRenameDialogOpen(true);
  };

  const handleConfirmRename = () => {
    if (renameTarget) {
      renameSaved(renameTarget.id, renameName);
    }
    setRenameDialogOpen(false);
    setRenameTarget(null);
  };

  const handleDelete = (id) => {
    deleteSaved(id);
  };

  const handleReset = () => {
    reset();
    setViewingSaved(false);
  };

  if (studyGuide) {
    return (
      <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
        <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
          <Button onClick={handleReset}>Generate Another</Button>
          {!viewingSaved && (
            <Button
              variant="outlined"
              startIcon={<SaveIcon />}
              onClick={handleSave}
            >
              Save
            </Button>
          )}
          <Button
            variant="contained"
            color="secondary"
            startIcon={<RecordVoiceOverIcon />}
            onClick={() => navigate("/voice", { state: { studyGuide } })}
          >
            Quiz me by voice
          </Button>
        </Stack>
        <StudyGuideView studyGuide={studyGuide} />

        <Dialog open={saveDialogOpen} onClose={() => setSaveDialogOpen(false)} maxWidth="sm" fullWidth>
          <DialogTitle>Save Study Guide</DialogTitle>
          <DialogContent>
            <TextField
              autoFocus
              fullWidth
              label="Display Name"
              value={saveName}
              onChange={(e) => setSaveName(e.target.value)}
              sx={{ mt: 1 }}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleConfirmSave();
              }}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setSaveDialogOpen(false)}>Cancel</Button>
            <Button variant="contained" onClick={handleConfirmSave}>
              Save
            </Button>
          </DialogActions>
        </Dialog>
      </Container>
    );
  }

  return (
    <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h1" gutterBottom>
        Study Guide
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Select materials and configure options to generate a personalized study guide.
      </Typography>

      {passedIds.length === 0 && (
        <>
          <Typography variant="h6" sx={{ mb: 1 }}>
            Select Materials
          </Typography>
          <MaterialList
            materials={materials}
            selectedIds={selectedIds}
            onSelectionChange={setSelectedIds}
            loading={materialsLoading}
          />
          <Divider sx={{ my: 3 }} />
        </>
      )}

      {passedIds.length > 0 && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {selectedIds.length} material{selectedIds.length !== 1 ? "s" : ""} selected from Materials page.
        </Typography>
      )}

      <Box sx={{ mb: 3 }}>
        <TextField
          fullWidth
          label="Focus Topics (optional, comma-separated)"
          placeholder="e.g., cell division, mitosis vs meiosis"
          value={focusTopics}
          onChange={(e) => setFocusTopics(e.target.value)}
          sx={{ mb: 2 }}
        />

        <Typography variant="body2" sx={{ mb: 1 }}>
          Detail Level
        </Typography>
        <ToggleButtonGroup
          value={detailLevel}
          exclusive
          onChange={(_, val) => val && setDetailLevel(val)}
          size="small"
        >
          <ToggleButton value="brief">Brief</ToggleButton>
          <ToggleButton value="standard">Standard</ToggleButton>
          <ToggleButton value="detailed">Detailed</ToggleButton>
        </ToggleButtonGroup>
      </Box>

      <Button
        variant="contained"
        size="large"
        startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <AutoStoriesIcon />}
        onClick={handleGenerate}
        disabled={selectedIds.length === 0 || loading}
      >
        {loading ? "Generating..." : "Generate Study Guide"}
      </Button>

      {error && (
        <Alert severity="error" sx={{ mt: 2 }} onClose={() => reset()}>
          {error}
        </Alert>
      )}

      {savedGuides.length > 0 && (
        <>
          <Divider sx={{ my: 4 }} />
          <Typography variant="h6" sx={{ mb: 2 }}>
            Saved Study Guides
          </Typography>
          <Grid container spacing={2}>
            {savedGuides.map((entry) => (
              <Grid key={entry.id} size={{ xs: 12, sm: 6 }}>
                <Card variant="outlined">
                  <CardContent sx={{ pb: 1 }}>
                    <Typography variant="subtitle1" noWrap title={entry.displayName}>
                      {entry.displayName}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {new Date(entry.savedAt).toLocaleDateString()} &middot;{" "}
                      {entry.studyGuide?.sections?.length || 0} sections
                    </Typography>
                  </CardContent>
                  <CardActions sx={{ pt: 0 }}>
                    <Button
                      size="small"
                      startIcon={<VisibilityIcon />}
                      onClick={() => handleViewSaved(entry)}
                    >
                      View
                    </Button>
                    <IconButton size="small" onClick={() => handleOpenRename(entry)} title="Rename">
                      <EditIcon fontSize="small" />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => handleDelete(entry.id)}
                      title="Delete"
                      color="error"
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </CardActions>
                </Card>
              </Grid>
            ))}
          </Grid>
        </>
      )}

      <Dialog open={renameDialogOpen} onClose={() => setRenameDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Rename Study Guide</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            label="Display Name"
            value={renameName}
            onChange={(e) => setRenameName(e.target.value)}
            sx={{ mt: 1 }}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleConfirmRename();
            }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRenameDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleConfirmRename}>
            Save
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={saveSuccess}
        autoHideDuration={3000}
        onClose={() => setSaveSuccess(false)}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        <Alert severity="success" variant="filled" onClose={() => setSaveSuccess(false)}>
          Study guide saved! Returning to your saved guides...
        </Alert>
      </Snackbar>
    </Container>
  );
}

export default StudyGuidePage;
