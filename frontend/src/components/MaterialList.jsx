import React, { useState, useEffect } from "react";
import {
  Box,
  Checkbox,
  Typography,
  Skeleton,
  Stack,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Button,
} from "@mui/material";
import ImageIcon from "@mui/icons-material/Image";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import MenuBookIcon from "@mui/icons-material/MenuBook";
import FolderOpenIcon from "@mui/icons-material/FolderOpen";
import VisibilityIcon from "@mui/icons-material/Visibility";
import EditIcon from "@mui/icons-material/Edit";
import CloseIcon from "@mui/icons-material/Close";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import apiClient from "../api/client";
import { getAllLabels, setLabel } from "../utils/materialLabels";

function getFileMeta(contentType) {
  if (contentType?.startsWith("image/")) {
    return { icon: <ImageIcon color="primary" fontSize="small" />, label: "Image" };
  }
  if (contentType === "application/pdf") {
    return { icon: <PictureAsPdfIcon color="error" fontSize="small" />, label: "PDF" };
  }
  if (contentType === "application/epub+zip") {
    return { icon: <MenuBookIcon color="secondary" fontSize="small" />, label: "EPUB" };
  }
  return { icon: <ImageIcon color="action" fontSize="small" />, label: "File" };
}

function formatSize(bytes) {
  if (!bytes) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

// Columns hidden on phones so the document name keeps the room.
const wideOnly = { display: { xs: "none", sm: "table-cell" } };

function MaterialList({ materials, selectedIds, onSelectionChange, loading, onDelete }) {
  const [labels, setLabels] = useState({});
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [previewMaterial, setPreviewMaterial] = useState(null);
  const [editOpen, setEditOpen] = useState(false);
  const [editMaterial, setEditMaterial] = useState(null);
  const [editValue, setEditValue] = useState("");
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [materialToDelete, setMaterialToDelete] = useState(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  const handleOpenDelete = (e, material) => {
    e.stopPropagation();
    setMaterialToDelete(material);
    setDeleteOpen(true);
  };

  const handleCloseDelete = () => {
    setDeleteOpen(false);
    setMaterialToDelete(null);
  };

  const handleConfirmDelete = async () => {
    if (!materialToDelete || !onDelete) return;
    setDeleteLoading(true);
    try {
      await onDelete(materialToDelete.id);
      handleCloseDelete();
    } catch (err) {
      console.error("Failed to delete material:", err);
    } finally {
      setDeleteLoading(false);
    }
  };

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
      <Stack spacing={1}>
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} variant="rounded" height={52} />
        ))}
      </Stack>
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
  const someSelected = selectedIds.length > 0 && !allSelected;

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
      <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 1 }}>
        <Typography variant="body2" color="text.secondary">
          {selectedIds.length > 0
            ? `${selectedIds.length} of ${materials.length} selected`
            : `${materials.length} document${materials.length === 1 ? "" : "s"}`}
        </Typography>
      </Stack>

      <TableContainer component={Paper} variant="outlined">
        <Table size="small" aria-label="Uploaded materials">
          <TableHead>
            <TableRow>
              <TableCell padding="checkbox">
                <Checkbox
                  checked={allSelected}
                  indeterminate={someSelected}
                  onChange={toggleAll}
                  inputProps={{ "aria-label": "select all materials" }}
                />
              </TableCell>
              <TableCell>Document</TableCell>
              <TableCell sx={wideOnly}>Type</TableCell>
              <TableCell sx={wideOnly} align="right">
                Size
              </TableCell>
              <TableCell align="right" sx={{ whiteSpace: "nowrap" }}>
                Actions
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {materials.map((material) => {
              const isSelected = selectedIds.includes(material.id);
              const label = labels[material.id];
              const displayName = label || material.filename;
              const { icon, label: typeLabel } = getFileMeta(material.content_type);
              return (
                <TableRow
                  key={material.id}
                  hover
                  selected={isSelected}
                  onClick={() => toggleSelect(material.id)}
                  sx={{ cursor: "pointer" }}
                >
                  <TableCell padding="checkbox">
                    <Checkbox
                      checked={isSelected}
                      onChange={() => toggleSelect(material.id)}
                      onClick={(e) => e.stopPropagation()}
                      inputProps={{ "aria-label": `select ${displayName}` }}
                    />
                  </TableCell>
                  <TableCell sx={{ py: 1 }}>
                    <Stack direction="row" spacing={1} alignItems="flex-start">
                      <Box sx={{ pt: "2px", flexShrink: 0 }}>{icon}</Box>
                      <Box sx={{ minWidth: 0 }}>
                        <Typography
                          variant="body2"
                          sx={{ fontWeight: 500, overflowWrap: "anywhere" }}
                        >
                          {displayName}
                        </Typography>
                        {label && (
                          <Typography
                            variant="caption"
                            color="text.secondary"
                            sx={{ display: "block", overflowWrap: "anywhere" }}
                          >
                            {material.filename}
                          </Typography>
                        )}
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          sx={{ display: { xs: "block", sm: "none" } }}
                        >
                          {typeLabel}
                          {material.size_bytes ? ` · ${formatSize(material.size_bytes)}` : ""}
                        </Typography>
                      </Box>
                    </Stack>
                  </TableCell>
                  <TableCell sx={wideOnly}>
                    <Typography variant="body2" color="text.secondary">
                      {typeLabel}
                    </Typography>
                  </TableCell>
                  <TableCell sx={{ ...wideOnly, whiteSpace: "nowrap" }} align="right">
                    <Typography variant="body2" color="text.secondary">
                      {formatSize(material.size_bytes)}
                    </Typography>
                  </TableCell>
                  <TableCell align="right" sx={{ whiteSpace: "nowrap", py: 0.5 }}>
                    <Tooltip title="Preview">
                      <IconButton size="small" onClick={(e) => handlePreview(e, material)}>
                        <VisibilityIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Edit label">
                      <IconButton size="small" onClick={(e) => handleOpenEdit(e, material)}>
                        <EditIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    {onDelete && (
                      <Tooltip title="Delete">
                        <IconButton
                          size="small"
                          color="error"
                          onClick={(e) => handleOpenDelete(e, material)}
                        >
                          <DeleteOutlineIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Image Preview Dialog */}
      <Dialog open={previewOpen} onClose={handleClosePreview} maxWidth="lg">
        <DialogTitle sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 2 }}>
          <Box sx={{ overflowWrap: "anywhere" }}>
            {labels[previewMaterial?.id] || previewMaterial?.filename || "Preview"}
          </Box>
          <IconButton onClick={handleClosePreview} size="small" aria-label="close preview">
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
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2, overflowWrap: "anywhere" }}>
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

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteOpen} onClose={handleCloseDelete}>
        <DialogTitle>Delete Document</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ overflowWrap: "anywhere" }}>
            Are you sure you want to delete{" "}
            <strong>
              {labels[materialToDelete?.id] || materialToDelete?.filename}
            </strong>
            ? This will remove it from Firebase Storage.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDelete} disabled={deleteLoading}>
            Cancel
          </Button>
          <Button
            onClick={handleConfirmDelete}
            color="error"
            variant="contained"
            disabled={deleteLoading}
          >
            {deleteLoading ? "Deleting…" : "Delete"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default MaterialList;
