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
