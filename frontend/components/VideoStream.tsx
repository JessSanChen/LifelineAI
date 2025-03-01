"use client";

import React, { useEffect, useRef, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { styled } from "@mui/material/styles";

const VideoContainer = styled(Box)(({ theme }) => ({
  width: "100%",
  height: "100%",
  position: "relative",
  backgroundColor: "black",
  borderRadius: theme.shape.borderRadius,
  overflow: "hidden",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
}));

// Normal image
const VideoImage = styled("img")({
  width: "100%",
  height: "100%",
  objectFit: "cover",
  borderRadius: "inherit",
});

// Pixelated + Blur overlay image
const PixelatedBlurImage = styled("img")({
  position: "absolute",
  top: 0,
  left: 0,

  // Make it smaller, then scale up to fill container
  // This is what introduces a “blocky” effect when combined with `image-rendering: pixelated`.
  width: "40%",             // experiment: try 20% or 50%
  height: "40%",
  transform: "scale(2.5)",  // if width=40%, scale(2.5) ~ 100%. Adjust as needed.
  transformOrigin: "top left",

  objectFit: "cover",
  borderRadius: "inherit",
  imageRendering: "pixelated",

  // Add a blur for a more jumbled effect
  filter: "blur(3px)",

  // Start invisible
  opacity: 0,
  transition: "opacity 0.3s ease-in-out",

  pointerEvents: "none", // so it doesn’t capture clicks
});

export default function VideoStream() {
  const [imageSrc, setImageSrc] = useState<string | null>(null);

  // State for controlling the pixel-blur overlay
  const [showPixelatedBlur, setShowPixelatedBlur] = useState(false);

  // Whether the frame rate changed “up” or “down”
  const [frameRateChange, setFrameRateChange] = useState<"increase" | "decrease" | null>(null);
  const oldFrameRateRef = useRef<number | null>(null);

  //
  // 1) WebSocket for the video feed
  //
  useEffect(() => {
    const ws = new WebSocket("ws://localhost:5001/video_feed");
    ws.onmessage = (event: MessageEvent) => {
      setImageSrc(`data:image/jpeg;base64,${event.data}`);
    };
    return () => {
      ws.close();
    };
  }, []);

  //
  // 2) WebSocket for frame rate updates
  //
  useEffect(() => {
    const ws2 = new WebSocket("ws://localhost:5001/frame_update");
    ws2.onmessage = (event: MessageEvent) => {
      const newFrameRate = parseInt(event.data, 10);

      if (oldFrameRateRef.current !== null) {
        if (newFrameRate > oldFrameRateRef.current) {
          setFrameRateChange("increase");
          triggerPixelation();
        } else if (newFrameRate < oldFrameRateRef.current) {
          setFrameRateChange("decrease");
          triggerPixelation();
        }
      }
      oldFrameRateRef.current = newFrameRate;
    };

    return () => {
      ws2.close();
    };
  }, []);

  //
  // Show “pixelated blur” overlay for about 2s, then hide it
  //
  const triggerPixelation = () => {
    setShowPixelatedBlur(true);

    // Hide after 2s
    setTimeout(() => {
      setShowPixelatedBlur(false);
      setFrameRateChange(null);
    }, 2000);
  };

  return (
    <VideoContainer>
      {/* Normal video or a loading message */}
      {imageSrc ? (
        <VideoImage src={imageSrc} alt="Live Stream" />
      ) : (
        <Typography color="white">Waiting for camera stream...</Typography>
      )}

      {/* Pixel-blur overlay (same src) */}
      {imageSrc && (
        <PixelatedBlurImage
          src={imageSrc}
          alt="Pixelated Blur Overlay"
          style={{ opacity: showPixelatedBlur ? 1 : 0 }}
        />
      )}

      {/* Frame rate bubble */}
      {frameRateChange && (
        <Box
          sx={{
            position: "absolute",
            top: "1rem",
            right: "1rem",
            py: 0.5,
            px: 1,
            borderRadius: "9999px",
            color: "white",
            backgroundColor: frameRateChange === "increase" ? "green" : "red",
            boxShadow: "0 0 8px rgba(0,0,0,0.4)",
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
