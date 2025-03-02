"use client";

import { useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Card from "@mui/material/Card";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import { styled } from "@mui/material/styles";
import VideoStream from "./VideoStream"; // Import the new video component

const VideoCard = styled(Card)(({ theme }) => ({
  flex: 3, // Larger space
  backgroundColor: "black",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  borderRadius: theme.shape.borderRadius,
  overflow: "hidden",
  boxShadow: theme.shadows[3],
}));

const TextCard = styled(Card)(({ theme }) => ({
  flex: 1, // Smaller space
  padding: theme.spacing(2),
  backgroundColor: theme.palette.background.paper,
  borderRadius: theme.shape.borderRadius,
  boxShadow: theme.shadows[2],
}));

const ChatBox = styled(Paper)(({ theme }) => ({
  flex: 3,
  display: "flex",
  flexDirection: "column",
  padding: theme.spacing(2),
  borderRadius: theme.shape.borderRadius,
  backgroundColor: theme.palette.background.paper,
  boxShadow: theme.shadows[3],
}));

const ChatMessagesContainer = styled(Box)(({ theme }) => ({
  display: "flex",
  flexDirection: "column",
  gap: theme.spacing(2),
  height: "100%",
}));

const AIChatMessages = styled(Box)(({ theme }) => ({
  flex: 1,
  overflowY: "auto",
  backgroundColor: theme.palette.background.default,
  padding: theme.spacing(2),
  borderRadius: theme.shape.borderRadius,
  border: "1px solid " + theme.palette.divider,
}));

const UserChatMessages = styled(Box)(({ theme }) => ({
  flex: 1,
  overflowY: "auto",
  backgroundColor: theme.palette.background.default,
  padding: theme.spacing(2),
  borderRadius: theme.shape.borderRadius,
  border: "1px solid " + theme.palette.divider,
}));

export default function Dashboard() {
  const [aiMessages, setAiMessages] = useState<string[]>([]);
  const [userMessages, setUserMessages] = useState<string[]>([]);
  const [fallDetectedMessage, setFallDetectedMessage] = useState<string>("");

  useEffect(() => {
    const socket = new WebSocket("ws://localhost:5001/triage");

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.speaker === "ai") {
        setAiMessages((prev) => [...prev, data.text]);
      } else if (data.speaker === "user") {
        setUserMessages((prev) => [...prev, data.text]);
      }
    };

    return () => {
      socket.close();
    };
  }, []);

  useEffect(() => {
    const socket = new WebSocket("ws://localhost:5001/fall_detected")

    socket.onmessage = (event) => {
      setFallDetectedMessage("FALL DETECTED");
    };

    return () => {
      socket.close();
    }
  })

  return (
    <Container id="triage" sx={{ py: { xs: 4, sm: 8 }, height: "100vh" }}>
      <Box
        sx={{
          display: "flex",
          flexDirection: { xs: "column", md: "row" },
          gap: 2,
          height: "100%",
        }}
      >
        {/* Left Side - Video + Text */}
        <Box sx={{ flex: 7, display: "flex", flexDirection: "column", gap: 2 }}>
          {/* Video Section */}
          <VideoCard>
            <VideoStream />
          </VideoCard>

          {/* Text Display Section */}
          <TextCard>
            <Typography variant="body1">{fallDetectedMessage}</Typography>
          </TextCard>
        </Box>

        {/* Right Side - Chatbox */}
        <ChatBox>
          <Typography variant="h6" gutterBottom>
            Chatbox
          </Typography>
          <ChatMessagesContainer>
            <AIChatMessages>
              <Typography variant="h6">AI Agent</Typography>
              {aiMessages.map((msg, index) => (
                <Typography key={index} variant="body2">
                  {msg}
                </Typography>
              ))}
            </AIChatMessages>

            <UserChatMessages>
              <Typography variant="h6">Patient</Typography>
              {userMessages.map((msg, index) => (
                <Typography key={index} variant="body2">
                  {msg}
                </Typography>
              ))}
            </UserChatMessages>
          </ChatMessagesContainer>
        </ChatBox>
      </Box>
    </Container>
  );
}
