import React, { useState, useRef } from "react";
import {
  Box,
  Button,
  Typography,
  LinearProgress,
  Alert,
  Stack,
  TextField,
  IconButton,
  Paper,
} from "@mui/material";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import InsertDriveFileIcon from "@mui/icons-material/InsertDriveFile";
import DeleteIcon from "@mui/icons-material/Delete";
import useUpload from "../hooks/useUpload";
import { setLabel } from "../utils/materialLabels";

const ACCEPT = ".jpg,.jpeg,.png,.webp,.pdf,.epub";

function MaterialUpload({ onUploadComplete }) {
  const { uploadFiles, loading, error, progress, reset } = useUpload();
  const [dragOver, setDragOver] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [fileLabels, setFileLabels] = useState({});
  const inputRef = useRef(null);

  const handleFiles = (files) => {
    if (files.length > 0) {
      const newFiles = Array.from(files);
      setSelectedFiles((prev) => [...prev, ...newFiles]);
      reset();
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    handleFiles(e.dataTransfer.files);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  const handleInputChange = (e) => {
    handleFiles(e.target.files);
    e.target.value = "";
  };

  const handleLabelChange = (index, value) => {
    setFileLabels((prev) => ({
      ...prev,
      [index]: value,
    }));
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) return;
    const data = await uploadFiles(selectedFiles);
    if (data) {
      if (data.materials) {
        data.materials.forEach((material, index) => {
          const label = fileLabels[index];
          if (label && label.trim()) {
            setLabel(material.id, label.trim());
          }
        });
      }
      setSelectedFiles([]);
      setFileLabels({});
      onUploadComplete?.(data);
    }
  };

  const removeFile = (index) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
    setFileLabels((prev) => {
      const newLabels = {};
      Object.keys(prev).forEach((key) => {
        const keyNum = parseInt(key, 10);
        if (keyNum < index) {
          newLabels[keyNum] = prev[key];
        } else if (keyNum > index) {
          newLabels[keyNum - 1] = prev[key];
        }
      });
      return newLabels;
    });
  };

  return (
    <Box>
      <Box
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => inputRef.current?.click()}
        sx={{
          border: "2px dashed",
          borderColor: dragOver ? "primary.main" : "divider",
          borderRadius: 2,
          p: 4,
          textAlign: "center",
          cursor: "pointer",
          bgcolor: dragOver ? "action.hover" : "transparent",
          transition: "all 0.2s",
          "&:hover": { borderColor: "primary.main", bgcolor: "action.hover" },
        }}
      >
        <CloudUploadIcon sx={{ fontSize: 48, color: "text.secondary", mb: 1 }} />
        <Typography variant="body1" gutterBottom>
          Drag & drop files here, or click to browse
        </Typography>
        <Typography variant="body2" color="text.secondary">
          JPEG, PNG, WebP, PDF, EPUB — up to 20 MB each
        </Typography>
      </Box>

      <input
        ref={inputRef}
        type="file"
        multiple
        accept={ACCEPT}
        onChange={handleInputChange}
        style={{ display: "none" }}
      />

      {selectedFiles.length > 0 && (
        <Stack spacing={1.5} sx={{ mt: 2 }}>
          {selectedFiles.map((file, i) => (
            <Paper key={`${file.name}-${i}`} variant="outlined" sx={{ p: 1.5 }}>
              <Stack direction="row" alignItems="center" spacing={1.5}>
                <InsertDriveFileIcon color="action" />
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Typography variant="body2" sx={{ overflowWrap: "anywhere" }}>
                    {file.name}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {(file.size / 1024 / 1024).toFixed(1)} MB
                  </Typography>
                </Box>
                <TextField
                  size="small"
                  placeholder="Label (optional)"
                  value={fileLabels[i] || ""}
                  onChange={(e) => handleLabelChange(i, e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                  sx={{ width: 180 }}
                />
                <IconButton size="small" onClick={() => removeFile(i)}>
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </Stack>
            </Paper>
          ))}
        </Stack>
      )}

      {selectedFiles.length > 0 && !loading && (
        <Button
          variant="contained"
          onClick={handleUpload}
          startIcon={<CloudUploadIcon />}
          sx={{ mt: 2 }}
        >
          Upload {selectedFiles.length} file{selectedFiles.length > 1 ? "s" : ""}
        </Button>
      )}

      {loading && (
        <Box sx={{ mt: 2 }}>
          <LinearProgress variant={progress < 80 ? "determinate" : "indeterminate"} value={progress} />
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            Uploading...
          </Typography>
        </Box>
      )}

      {error && (
        <Alert severity="error" sx={{ mt: 2 }} onClose={reset}>
          {error}
        </Alert>
      )}
    </Box>
  );
}

export default MaterialUpload;
