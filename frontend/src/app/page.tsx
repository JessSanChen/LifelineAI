"use client"; // Ensures this component runs on the client side

import React, { useEffect, useState } from "react";

// import * as React from 'react';
import CssBaseline from '@mui/material/CssBaseline';
import Divider from '@mui/material/Divider';
import AppTheme from '../../theme/AppTheme';
import Hero from '../../components/Hero';
import AppAppBar from '../../components/AppAppBar';
import Dashboard from '../../components/Dashboard';


export default function Home(props: { disableCustomTheme?: boolean }) {
  const [imageSrc, setImageSrc] = useState<string | null>(null);

  useEffect(() => {
    // Open a WebSocket connection to the Python server
    const ws = new WebSocket("ws://localhost:5001/video_feed");

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
    <AppTheme {...props}>
      <CssBaseline enableColorScheme />

      <AppAppBar />
      <Hero />
      <div>
        <Dashboard />
        {/* <Divider /> */}
      </div>

    </AppTheme>

  );
}
