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
} from "@mui/material";
import AutoStoriesIcon from "@mui/icons-material/AutoStories";
import QuizIcon from "@mui/icons-material/Quiz";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import CameraAltIcon from "@mui/icons-material/CameraAlt";
import MaterialUpload from "../components/MaterialUpload";
import MaterialList from "../components/MaterialList";
import CameraCapture from "../components/CameraCapture";
import useMaterials from "../hooks/useMaterials";
import useUpload from "../hooks/useUpload";

function MaterialsPage() {
  const { materials, loading, error, fetchMaterials } = useMaterials();
  const { uploadFiles } = useUpload();
  const [selectedIds, setSelectedIds] = useState([]);
  const [tab, setTab] = useState(0);
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

  return (
    <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h1" gutterBottom>
        My Materials
      </Typography>

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
    </Container>
  );
}

export default MaterialsPage;
