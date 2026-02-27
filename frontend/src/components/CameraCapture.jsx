import React from "react";

/**
 * CameraCapture component -- integrates with device camera for capturing photos of notes.
 *
 * Uses the MediaDevices API (navigator.mediaDevices.getUserMedia) to access
 * the device camera, show a live preview, and capture photos.
 *
 * TODO: Implement with:
 * - Video element for live camera preview
 * - Canvas element for capturing frames
 * - MUI Fab (floating action button) for capture trigger
 * - Preview of captured photo with accept/retake options
 * - Auto-upload on accept via useUpload hook
 * - Permission request handling (camera access dialog)
 * - Fallback to file picker on devices without camera or when permission denied
 * - Rear camera preference (facingMode: "environment") for note scanning
 * - Clean up: stop media stream on unmount
 *
 * Mobile considerations:
 * - Full-screen camera view on mobile
 * - Touch-friendly capture button
 * - iOS Safari compatibility (requires user gesture for getUserMedia)
 */
function CameraCapture({ onCapture }) {
  // TODO: Implement camera capture with preview and upload
  return (
    <div>
      <p>TODO: Implement CameraCapture component with device camera integration.</p>
    </div>
  );
}

export default CameraCapture;
