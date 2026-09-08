import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Container,
  Typography,
  Button,
  Stack,
  Divider,
  Tabs,
  Tab,
  Box,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
  Alert,
} from "@mui/material";
import AutoStoriesIcon from "@mui/icons-material/AutoStories";
import QuizIcon from "@mui/icons-material/Quiz";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import CameraAltIcon from "@mui/icons-material/CameraAlt";
import DeleteSweepIcon from "@mui/icons-material/DeleteSweep";
import MaterialUpload from "../components/MaterialUpload";
import MaterialList from "../components/MaterialList";
import CameraCapture from "../components/CameraCapture";
import useMaterials from "../hooks/useMaterials";
import useUpload from "../hooks/useUpload";

function MaterialsPage() {
  const { materials, loading, error, fetchMaterials, deleteMaterial, clearAllMaterials } = useMaterials();
  const { uploadFiles } = useUpload();
  const [selectedIds, setSelectedIds] = useState([]);
  const [tab, setTab] = useState(0);
  const [clearDialogOpen, setClearDialogOpen] = useState(false);
  const [clearLoading, setClearLoading] = useState(false);
  const [clearError, setClearError] = useState(null);
  const navigate = useNavigate();

  const handleUploadComplete = () => {
    fetchMaterials();
  };

  const handleCameraCapture = async (file) => {
    const data = await uploadFiles([file]);
    if (data) {
      fetchMaterials();
    }
  };

  const handleGenerateStudyGuide = () => {
    navigate("/study-guide", { state: { selectedIds } });
  };

  const handleGenerateQuiz = () => {
    navigate("/quiz", { state: { selectedIds } });
  };

  const handleClearAllConfirm = async () => {
    setClearLoading(true);
    setClearError(null);
    try {
      await clearAllMaterials();
      setSelectedIds([]);
      setClearDialogOpen(false);
    } catch (err) {
      console.error("Failed to clear materials:", err);
      setClearError(err.message || "Clear failed.");
    } finally {
      setClearLoading(false);
    }
  };

  return (
    <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        sx={{ mb: 2 }}
      >
        <Typography variant="h1" sx={{ fontSize: { xs: "2rem", sm: "2.5rem" } }}>
          My Materials
        </Typography>
        {materials.length > 0 && (
          <Button
            variant="outlined"
            color="error"
            size="small"
            startIcon={<DeleteSweepIcon />}
            onClick={() => setClearDialogOpen(true)}
          >
            Clear All Documents
          </Button>
        )}
      </Stack>

      {/* Upload tabs */}
      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
        <Tab icon={<CloudUploadIcon />} label="Upload Files" iconPosition="start" />
        <Tab icon={<CameraAltIcon />} label="Camera Capture" iconPosition="start" />
      </Tabs>

      {tab === 0 && <MaterialUpload onUploadComplete={handleUploadComplete} />}
      {tab === 1 && <CameraCapture onCapture={handleCameraCapture} />}

      <Divider sx={{ my: 3 }} />

      {/* Materials list */}
      <MaterialList
        materials={materials}
        selectedIds={selectedIds}
        onSelectionChange={setSelectedIds}
        loading={loading}
        onDelete={deleteMaterial}
      />

      {error && (
        <Typography color="error" sx={{ mt: 2 }}>
          Failed to load materials: {error}
        </Typography>
      )}

      {/* Action buttons */}
      {selectedIds.length > 0 && (
        <Stack direction="row" spacing={2} sx={{ mt: 3 }}>
          <Button
            variant="contained"
            startIcon={<AutoStoriesIcon />}
            onClick={handleGenerateStudyGuide}
          >
            Generate Study Guide
          </Button>
          <Button
            variant="contained"
            color="secondary"
            startIcon={<QuizIcon />}
            onClick={handleGenerateQuiz}
          >
            Generate Quiz
          </Button>
        </Stack>
      )}

      {/* Clear All Confirmation Dialog */}
      <Dialog
        open={clearDialogOpen}
        onClose={() => {
          setClearDialogOpen(false);
          setClearError(null);
        }}
      >
        <DialogTitle>Clear All Materials</DialogTitle>
        <DialogContent>
          <Typography variant="body2">
            Are you sure you want to delete all <strong>{materials.length}</strong> uploaded documents?
            This will remove them completely from Firebase Storage so you can start fresh.
          </Typography>
          {clearError && (
            <Alert severity="error" sx={{ mt: 2 }}>
              Could not clear: {clearError}
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setClearDialogOpen(false)} disabled={clearLoading}>
            Cancel
          </Button>
          <Button
            onClick={handleClearAllConfirm}
            color="error"
            variant="contained"
            disabled={clearLoading}
          >
            {clearLoading ? "Clearing…" : "Clear All"}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}

export default MaterialsPage;
