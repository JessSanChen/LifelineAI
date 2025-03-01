"use client"; // Ensures this component runs on the client side

import React, { useEffect, useState } from "react";

export default function Home() {
  const [imageSrc, setImageSrc] = useState<string | null>(null);

  useEffect(() => {
    // Open a WebSocket connection to the Python server
    const ws = new WebSocket("ws://localhost:5000/ws");

    // Listen for incoming messages (base64-encoded JPEGs)
    ws.onmessage = (event: MessageEvent) => {
      // Construct a data URL for the JPEG image
      setImageSrc(`data:image/jpeg;base64,${event.data}`);
    };

    // Cleanup on unmount
    return () => {
      ws.close();
    };
  }, []);

  return (
    <div style={{ textAlign: "center", marginTop: "2rem" }}>
      <h1>Live Camera Stream</h1>
      {imageSrc ? (
        <img
          src={imageSrc}
          alt="Camera Stream"
          style={{ border: "2px solid #000", maxWidth: "100%" }}
        />
      ) : (
        <p>Waiting for camera stream...</p>
      )}
    </div>
  );
}
