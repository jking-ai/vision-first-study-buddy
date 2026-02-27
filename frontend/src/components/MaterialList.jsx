import React, { useState, useEffect } from "react";
import {
  Box,
  Card,
  CardContent,
  Checkbox,
  Typography,
  Skeleton,
  Button,
  Stack,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  CircularProgress,
} from "@mui/material";
import Grid from "@mui/material/Grid2";
import ImageIcon from "@mui/icons-material/Image";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import MenuBookIcon from "@mui/icons-material/MenuBook";
import FolderOpenIcon from "@mui/icons-material/FolderOpen";
import VisibilityIcon from "@mui/icons-material/Visibility";
import EditIcon from "@mui/icons-material/Edit";
import CloseIcon from "@mui/icons-material/Close";
import apiClient from "../api/client";
import { getAllLabels, setLabel } from "../utils/materialLabels";

function getFileIcon(contentType) {
  if (contentType?.startsWith("image/")) return <ImageIcon color="primary" />;
  if (contentType === "application/pdf") return <PictureAsPdfIcon color="error" />;
  if (contentType === "application/epub+zip") return <MenuBookIcon color="secondary" />;
  return <ImageIcon color="action" />;
}

function formatSize(bytes) {
  if (!bytes) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function MaterialList({ materials, selectedIds, onSelectionChange, loading }) {
  const [labels, setLabels] = useState({});
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [previewMaterial, setPreviewMaterial] = useState(null);
  const [editOpen, setEditOpen] = useState(false);
  const [editMaterial, setEditMaterial] = useState(null);
  const [editValue, setEditValue] = useState("");

  useEffect(() => {
    setLabels(getAllLabels());
  }, [materials]);

  const handlePreview = async (e, material) => {
    e.stopPropagation();
    setPreviewMaterial(material);

    if (material.content_type?.startsWith("image/")) {
      setPreviewLoading(true);
      setPreviewOpen(true);
      try {
        const detail = await apiClient.getMaterial(material.id);
        setPreviewUrl(detail.preview_url);
      } catch (err) {
        console.error("Failed to load preview:", err);
        setPreviewUrl(null);
      } finally {
        setPreviewLoading(false);
      }
    } else {
      setPreviewLoading(true);
      try {
        const detail = await apiClient.getMaterial(material.id);
        if (detail.preview_url) {
          window.open(detail.preview_url, "_blank");
        }
      } catch (err) {
        console.error("Failed to get preview URL:", err);
      } finally {
        setPreviewLoading(false);
      }
    }
  };

  const handleClosePreview = () => {
    setPreviewOpen(false);
    setPreviewUrl(null);
    setPreviewMaterial(null);
  };

  const handleOpenEdit = (e, material) => {
    e.stopPropagation();
    setEditMaterial(material);
    setEditValue(labels[material.id] || "");
    setEditOpen(true);
  };

  const handleSaveLabel = () => {
    if (editMaterial) {
      setLabel(editMaterial.id, editValue);
      setLabels(getAllLabels());
    }
    setEditOpen(false);
    setEditMaterial(null);
  };

  const handleCloseEdit = () => {
    setEditOpen(false);
    setEditMaterial(null);
  };

  if (loading) {
    return (
      <Grid container spacing={2}>
        {[1, 2, 3].map((i) => (
          <Grid key={i} size={{ xs: 12, sm: 6, md: 4 }}>
            <Card>
              <CardContent>
                <Skeleton variant="circular" width={40} height={40} />
                <Skeleton variant="text" sx={{ mt: 1 }} />
                <Skeleton variant="text" width="60%" />
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    );
  }

  if (!materials || materials.length === 0) {
    return (
      <Box sx={{ textAlign: "center", py: 6 }}>
        <FolderOpenIcon sx={{ fontSize: 64, color: "text.disabled", mb: 2 }} />
        <Typography variant="h6" color="text.secondary">
          No materials uploaded yet
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Upload images, PDFs, or EPUBs to get started.
        </Typography>
      </Box>
    );
  }

  const allSelected = materials.length > 0 && selectedIds.length === materials.length;

  const toggleSelect = (id) => {
    if (selectedIds.includes(id)) {
      onSelectionChange(selectedIds.filter((sid) => sid !== id));
    } else {
      onSelectionChange([...selectedIds, id]);
    }
  };

  const toggleAll = () => {
    if (allSelected) {
      onSelectionChange([]);
    } else {
      onSelectionChange(materials.map((m) => m.id));
    }
  };

  return (
    <Box>
      <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2 }}>
        <Button size="small" onClick={toggleAll}>
          {allSelected ? "Clear All" : "Select All"}
        </Button>
        {selectedIds.length > 0 && (
          <Typography variant="body2" color="text.secondary">
            {selectedIds.length} of {materials.length} selected
          </Typography>
        )}
      </Stack>

      <Grid container spacing={2}>
        {materials.map((material) => {
          const isSelected = selectedIds.includes(material.id);
          const displayName = labels[material.id] || material.filename;
          return (
            <Grid key={material.id} size={{ xs: 12, sm: 6, md: 4 }}>
              <Card
                onClick={() => toggleSelect(material.id)}
                sx={{
                  cursor: "pointer",
                  outline: isSelected ? 2 : 0,
                  outlineColor: "primary.main",
                  transition: "outline 0.15s",
                  "&:hover": { elevation: 4 },
                }}
              >
                <CardContent sx={{ display: "flex", alignItems: "flex-start", gap: 1 }}>
                  <Checkbox
                    checked={isSelected}
                    onChange={() => toggleSelect(material.id)}
                    onClick={(e) => e.stopPropagation()}
                    size="small"
                  />
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1, flex: 1, minWidth: 0 }}>
                    {getFileIcon(material.content_type)}
                    <Box sx={{ minWidth: 0, flex: 1 }}>
                      <Typography variant="body2" noWrap title={displayName}>
                        {displayName}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {formatSize(material.size_bytes)}
                        {labels[material.id] && (
                          <span style={{ marginLeft: 8, fontStyle: "italic" }}>
                            ({material.filename})
                          </span>
                        )}
                      </Typography>
                    </Box>
                  </Box>
                  <Stack direction="row" spacing={0.5}>
                    <IconButton
                      size="small"
                      onClick={(e) => handlePreview(e, material)}
                      title="Preview"
                    >
                      <VisibilityIcon fontSize="small" />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={(e) => handleOpenEdit(e, material)}
                      title="Edit label"
                    >
                      <EditIcon fontSize="small" />
                    </IconButton>
                  </Stack>
                </CardContent>
              </Card>
            </Grid>
          );
        })}
      </Grid>

      {/* Image Preview Dialog */}
      <Dialog open={previewOpen} onClose={handleClosePreview} maxWidth="lg">
        <DialogTitle sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          {labels[previewMaterial?.id] || previewMaterial?.filename || "Preview"}
          <IconButton onClick={handleClosePreview} size="small">
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent sx={{ minWidth: 300, minHeight: 200, display: "flex", alignItems: "center", justifyContent: "center" }}>
          {previewLoading ? (
            <CircularProgress />
          ) : previewUrl ? (
            <img
              src={previewUrl}
              alt={previewMaterial?.filename}
              style={{ maxWidth: "100%", maxHeight: "70vh", objectFit: "contain" }}
            />
          ) : (
            <Typography color="text.secondary">Failed to load preview</Typography>
          )}
        </DialogContent>
      </Dialog>

      {/* Edit Label Dialog */}
      <Dialog open={editOpen} onClose={handleCloseEdit} maxWidth="sm" fullWidth>
        <DialogTitle>Edit Label</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Set a custom display name for "{editMaterial?.filename}"
          </Typography>
          <TextField
            autoFocus
            fullWidth
            label="Label"
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            placeholder={editMaterial?.filename}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                handleSaveLabel();
              }
            }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseEdit}>Cancel</Button>
          <Button onClick={handleSaveLabel} variant="contained">
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default MaterialList;
