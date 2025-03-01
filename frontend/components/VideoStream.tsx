"use client";

import React, { useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { styled } from "@mui/material/styles";

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

const VideoImage = styled("img")({
  width: "100%",
  height: "100%",
  objectFit: "cover",
  borderRadius: "inherit",
});

export default function VideoStream() {
  const [imageSrc, setImageSrc] = useState<string | null>(null);

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:5001/ws");

    ws.onmessage = (event: MessageEvent) => {
      setImageSrc(`data:image/jpeg;base64,${event.data}`);
    };

    return () => {
      ws.close();
    };
  }, []);

  return (
    <VideoContainer>
      {imageSrc ? (
        <VideoImage src={imageSrc} alt="Live Stream" />
      ) : (
        <Typography color="white">Waiting for camera stream...</Typography>
      )}
    </VideoContainer>
  );
}
