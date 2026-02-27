import React, { useState, useRef, useEffect, useCallback } from "react";
import {
  Box,
  Typography,
  Fab,
  Button,
  Stack,
  Alert,
} from "@mui/material";
import CameraAltIcon from "@mui/icons-material/CameraAlt";
import ReplayIcon from "@mui/icons-material/Replay";
import CheckIcon from "@mui/icons-material/Check";
import PhotoCameraIcon from "@mui/icons-material/PhotoCamera";

// State machine: idle -> streaming -> preview
const States = { IDLE: "idle", STREAMING: "streaming", PREVIEW: "preview" };

function CameraCapture({ onCapture }) {
  const [state, setState] = useState(States.IDLE);
  const [error, setError] = useState(null);
  const [capturedBlob, setCapturedBlob] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const fallbackRef = useRef(null);

  const stopStream = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopStream();
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [stopStream, previewUrl]);

  const startCamera = async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setState(States.STREAMING);
    } catch {
      setError("Camera access denied or unavailable. Use the file picker instead.");
      setState(States.IDLE);
    }
  };

  const capture = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0);

    canvas.toBlob(
      (blob) => {
        if (blob) {
          setCapturedBlob(blob);
          setPreviewUrl(URL.createObjectURL(blob));
          stopStream();
          setState(States.PREVIEW);
        }
      },
      "image/jpeg",
      0.9
    );
  };

  const retake = () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setCapturedBlob(null);
    setPreviewUrl(null);
    startCamera();
  };

  const accept = () => {
    if (capturedBlob) {
      const file = new File([capturedBlob], `capture-${Date.now()}.jpg`, {
        type: "image/jpeg",
      });
      onCapture?.(file);
    }
    // Reset
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setCapturedBlob(null);
    setPreviewUrl(null);
    setState(States.IDLE);
  };

  const handleFallbackInput = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      onCapture?.(file);
    }
    e.target.value = "";
  };

  return (
    <Box>
      {/* Idle state */}
      {state === States.IDLE && (
        <Box sx={{ textAlign: "center", py: 3 }}>
          <Stack direction="row" spacing={2} justifyContent="center">
            <Button
              variant="contained"
              startIcon={<CameraAltIcon />}
              onClick={startCamera}
            >
              Open Camera
            </Button>
            <Button
              variant="outlined"
              startIcon={<PhotoCameraIcon />}
              onClick={() => fallbackRef.current?.click()}
            >
              Choose Photo
            </Button>
          </Stack>
          <input
            ref={fallbackRef}
            type="file"
            accept="image/*"
            capture="environment"
            onChange={handleFallbackInput}
            style={{ display: "none" }}
          />
        </Box>
      )}

      {/* Streaming state */}
      {state === States.STREAMING && (
        <Box sx={{ position: "relative", textAlign: "center" }}>
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            style={{
              width: "100%",
              maxHeight: 400,
              borderRadius: 8,
              background: "#000",
              objectFit: "cover",
            }}
          />
          <Fab
            color="primary"
            onClick={capture}
            sx={{
              position: "absolute",
              bottom: 16,
              left: "50%",
              transform: "translateX(-50%)",
            }}
          >
            <CameraAltIcon />
          </Fab>
        </Box>
      )}

      {/* Preview state */}
      {state === States.PREVIEW && previewUrl && (
        <Box sx={{ textAlign: "center" }}>
          <img
            src={previewUrl}
            alt="Captured"
            style={{
              width: "100%",
              maxHeight: 400,
              borderRadius: 8,
              objectFit: "contain",
            }}
          />
          <Stack direction="row" spacing={2} justifyContent="center" sx={{ mt: 2 }}>
            <Button variant="outlined" startIcon={<ReplayIcon />} onClick={retake}>
              Retake
            </Button>
            <Button variant="contained" startIcon={<CheckIcon />} onClick={accept}>
              Use Photo
            </Button>
          </Stack>
        </Box>
      )}

      {/* Hidden canvas for capture */}
      <canvas ref={canvasRef} style={{ display: "none" }} />

      {/* Error */}
      {error && (
        <Alert severity="warning" sx={{ mt: 2 }}>
          {error}
          <Button
            size="small"
            sx={{ ml: 1 }}
            onClick={() => fallbackRef.current?.click()}
          >
            Open file picker
          </Button>
          <input
            ref={fallbackRef}
            type="file"
            accept="image/*"
            capture="environment"
            onChange={handleFallbackInput}
            style={{ display: "none" }}
          />
        </Alert>
      )}
    </Box>
  );
}

export default CameraCapture;
