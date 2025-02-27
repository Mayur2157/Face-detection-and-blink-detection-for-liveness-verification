const video = document.getElementById("video");
const startButton = document.getElementById("startButton");
const blinkCountValue = document.getElementById("blinkCountValue");
const livenessScoreValue = document.getElementById("livenessScoreValue");
const statusDisplay = document.getElementById("statusMessage");
const faceGuide = document.getElementById("face-guide");
const earValue = document.getElementById("earValue");
const blinkIndicator = document.getElementById("blinkIndicator");
const debugInfo = document.getElementById("debugInfo");

// Application state
let isDetecting = false;
let detectionInterval;
let lastBlinkCount = 0;
let lastEar = 0;

// Camera setup
async function setupCamera() {
    statusDisplay.textContent = "Connecting to camera...";
    statusDisplay.className = "status-message status-ready";
    
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ 
            video: { 
                width: { ideal: 640 },
                height: { ideal: 480 },
                facingMode: "user"
            } 
        });
        
        video.srcObject = stream;
        
        // Wait for video to be ready
        return new Promise((resolve) => {
            video.onloadedmetadata = () => {
                statusDisplay.textContent = "Camera connected. Click 'Start Detection' to begin.";
                statusDisplay.className = "status-message status-ready";
                resolve(true);
            };
        });
    } catch (error) {
        console.error("Error accessing webcam:", error);
        statusDisplay.textContent = "Error: Cannot access camera. Please allow camera permissions.";
        statusDisplay.className = "status-message status-error";
        return false;
    }
}

// Reset counters
function resetCounters() {
    fetch("/reset", {
        method: "POST"
    })
        .then(response => response.json())
        .then(data => {
            updateMetrics(0, 0, 0);
            lastBlinkCount = 0;
        })
        .catch(error => {
            console.error("Error resetting:", error);
            showError("Failed to reset counters. Please refresh the page.");
        });
}

// Update the UI metrics
function updateMetrics(blinkCount, livenessScore, ear) {
    blinkCountValue.textContent = blinkCount;
    livenessScoreValue.textContent = livenessScore;
    
    // Update EAR meter
    const earPercent = Math.max(Math.min(ear * 300, 100), 0);
    earValue.style.width = `${earPercent}%`;
    
    // Show debug info
    debugInfo.textContent = `EAR: ${ear.toFixed(3)}`;
    
    // Blink indicator
    if (blinkCount > lastBlinkCount) {
        blinkIndicator.classList.add("blink-active");
        lastBlinkCount = blinkCount;
        
        // Remove the animation class after animation completes
        setTimeout(() => {
            blinkIndicator.classList.remove("blink-active");
        }, 500);
    }
    
    // Update face guide color based on EAR
    if (ear < 0.30 && ear > 0) {
        faceGuide.classList.add("guide-active");
    } else {
        faceGuide.classList.remove("guide-active");
    }
    
    // Update last known EAR
    lastEar = ear;
}

// Start Detection
function toggleDetection() {
    isDetecting = !isDetecting;
    
    if (isDetecting) {
        resetCounters();
        startButton.innerText = "Stop Detection";
        statusDisplay.textContent = "Detecting... Please look at the camera and blink normally.";
        statusDisplay.className = "status-message status-active";
        detectionInterval = setInterval(sendFrameToServer, 150); // Send frame every 150ms
    } else {
        startButton.innerText = "Start Detection";
        statusDisplay.textContent = "Detection stopped.";
        statusDisplay.className = "status-message status-ready";
        clearInterval(detectionInterval);
    }
}

// Show error message
function showError(message) {
    statusDisplay.textContent = message;
    statusDisplay.className = "status-message status-error";
}

// Send frames to server
function sendFrameToServer() {
    if (!isDetecting) return;

    try {
        // Create canvas and draw video frame
        const canvas = document.createElement("canvas");
        const context = canvas.getContext("2d");
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);

        // Get base64 representation
        const frameData = canvas.toDataURL("image/jpeg", 0.8); // Reduced quality for better performance

        // Send to server
        fetch("/detect", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ frame: frameData })
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Server error: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.error === "No face detected") {
                    statusDisplay.textContent = "No face detected. Please center your face in the frame.";
                    statusDisplay.className = "status-message status-warning";
                } else if (data.error) {
                    console.error("Server Error:", data.error);
                    statusDisplay.textContent = "Error: " + data.error;
                    statusDisplay.className = "status-message status-error";
                } else {
                    statusDisplay.textContent = "Face detected! Blink naturally...";
                    statusDisplay.className = "status-message status-success";
                }
                
                // Update metrics
                updateMetrics(
                    data.blink_count || 0, 
                    data.liveness_score || 0, 
                    data.ear || lastEar
                );
                
                // Update verification status
                if (data.liveness_score >= 30) {
                    statusDisplay.textContent = "✅ Liveness Verified!";
                    statusDisplay.className = "status-message status-verified";
                }
            })
            .catch(error => {
                console.error("Error sending frame:", error);
                showError("Connection error. Please try again.");
            });
    } catch (error) {
        console.error("Error processing frame:", error);
        showError("Error processing video frame.");
    }
}

// Initialize the application
async function init() {
    // Setup camera first
    const cameraReady = await setupCamera();
    
    if (cameraReady) {
        // Add event listeners
        startButton.addEventListener("click", toggleDetection);
        
        // Enable debug mode with keyboard shortcut (Shift + D)
        document.addEventListener("keydown", (e) => {
            if (e.shiftKey && e.key === "D") {
                debugInfo.style.display = debugInfo.style.display === "block" ? "none" : "block";
            }
        });
    } else {
        startButton.disabled = true;
    }
}

// Start the application
window.addEventListener("DOMContentLoaded", init);