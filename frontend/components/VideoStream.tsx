"use client";

import React, { useEffect, useRef, useState } from "react";
import { styled, keyframes } from "@mui/system";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

// ---------------------------------------------
// 1) Define the container and image styles
// ---------------------------------------------
const VideoContainer = styled(Box)(({ theme }) => ({
  width: "100%",
  height: "100%",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  backgroundColor: "black",
  borderRadius: theme.shape.borderRadius,
  overflow: "hidden",
  position: "relative",
}));

// A keyframe that starts the image at a heavily scaled-down size
// (making it appear pixelated via nearest-neighbor scaling), then
// scales it up to normal, and finally removes `image-rendering`.
const pixelationAnimation = keyframes`
  0% {
    transform: scale(0.2);
    image-rendering: pixelated;
  }
  50% {
    transform: scale(1);
    image-rendering: pixelated;
  }
  100% {
    transform: scale(1);
    image-rendering: auto;
  }
`;

const VideoImage = styled("img")(({ theme }) => ({
  width: "100%",
  height: "100%",
  objectFit: "cover",
  borderRadius: "inherit",
  transition: "transform 0.3s ease-in-out", // fallback transition for minor scale changes
  "&.pixelate": {
    // Once we set the 'pixelate' class, run the pixelation keyframe
    animation: `${pixelationAnimation} 2s forwards`,
  },
}));

// ---------------------------------------------
// 2) The main component
// ---------------------------------------------
export default function VideoStream() {
  const [imageSrc, setImageSrc] = useState<string | null>(null);

  // State for controlling pixelation animation
  const [pixelate, setPixelate] = useState(false);

  // State for whether the frame rate went up or down
  //  - 'increase' | 'decrease' | null
  const [frameRateChange, setFrameRateChange] = useState<null | "increase" | "decrease">(null);

  // Store the old frame rate in a ref so changing it doesn't cause re-renders
  const oldFrameRateRef = useRef<number | null>(5);

  // ---------------------------------------------
  // 3) First WebSocket: get image frames
  // ---------------------------------------------
  useEffect(() => {
    const ws = new WebSocket("ws://localhost:5001/video_feed");
    ws.onmessage = (event: MessageEvent) => {
      // event.data is expected to be the Base64-encoded JPEG
      setImageSrc(`data:image/jpeg;base64,${event.data}`);
    };
    return () => {
      ws.close();
    };
  }, []);

  // ---------------------------------------------
  // 4) Second WebSocket: listen for frame rate updates
  // ---------------------------------------------
  useEffect(() => {
    const ws2 = new WebSocket("ws://localhost:5001/frame_update");

    ws2.onmessage = (event: MessageEvent) => {
      const newFrameRate = parseInt(event.data, 10);

      // If this isn't the first frame rate update,
      // check if the new frame rate is up or down.
      if (oldFrameRateRef.current !== null) {
        if (newFrameRate > oldFrameRateRef.current) {
          setFrameRateChange("increase");
          triggerPixelation();
        } else if (newFrameRate < oldFrameRateRef.current) {
          setFrameRateChange("decrease");
          triggerPixelation();
        } else {
          // If no change, you could handle it here (optional).
          // setFrameRateChange(null);
        }
      }

      // Always store the new frame rate for next comparison
      oldFrameRateRef.current = newFrameRate;
    };

    return () => {
      ws2.close();
    };
  }, []);

  // ---------------------------------------------
  // 5) Helper: briefly trigger pixelation & overlay
  // ---------------------------------------------
  const triggerPixelation = () => {
    setPixelate(true);

    // After 2s (match your animation duration), remove pixelation & overlay
    setTimeout(() => {
      setPixelate(false);
      setFrameRateChange(null);
    }, 2000);
  };

  // ---------------------------------------------
  // 6) Rendering
  // ---------------------------------------------
  return (
    <VideoContainer>
      {/* If we have an image, display it; otherwise show a "waiting" message */}
      {imageSrc ? (
        <VideoImage
          src={imageSrc}
          alt="Live Stream"
          className={pixelate ? "pixelate" : ""}
        />
      ) : (
        <Typography color="white">Waiting for camera stream...</Typography>
      )}

      {/* Frame rate change bubble overlay */}
      {frameRateChange && (
        <Box
          sx={{
            position: "absolute",
            top: "1rem",
            right: "1rem",
            padding: "0.4rem 0.8rem",
            borderRadius: "9999px",
            color: "white",
            backgroundColor: frameRateChange === "increase" ? "green" : "red",
            boxShadow: "0 0 8px rgba(0,0,0,0.4)",
            transition: "opacity 0.3s ease-in-out",
            fontWeight: "bold",
          }}
        >
          {frameRateChange === "increase"
            ? "Frame Rate Increased"
            : "Frame Rate Decreased"}
        </Box>
      )}
    </VideoContainer>
  );
}