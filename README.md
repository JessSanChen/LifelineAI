# LifelineAI - A real-time fall monitoring system for people at-risk

Lifeline AI is an end-to-end fall monitoring system that detects a fall from an at-risk person with real-time video monitoring using a Visual Language Model (VLM).
After detecting a possible fall, the system triages the situation by talking with the injured person and determines whether to contact emergency services.

## Innovations and Applications of Inference-Time Compute

1. We apply adaptive scaling to the VLM by scaling the sampling rate up and down depending on the content of the video. For example, if there is nothing happening in the frame, then the sampling rate is dynamically decreased. If people are walking around, the sampling rate and context window are increased to better assess the situation.
2. Our triaging agent continues to reason about the situation by asking questions to determine the severity of the fall and the situation, asking more questions as necessary and determining when to contact authorities through a process model reward system.
