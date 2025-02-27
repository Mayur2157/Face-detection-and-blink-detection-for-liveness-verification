from flask import Flask, render_template, request, jsonify
import cv2
import numpy as np
import base64
import logging
from blink_detector import BlinkDetector

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LivenessApp")

app = Flask(__name__)

# Initialize the blink detector
blink_detector = BlinkDetector(blink_threshold=0.30, blink_frames=2)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/detect', methods=['POST'])
def detect():
    try:
        # Get base64 image data from request
        data = request.get_json()
        if not data or 'frame' not in data:
            return jsonify({"error": "No frame data received"}), 400
            
        # Process base64 image
        base64_image = data['frame'].split(',')[1]
        image_data = base64.b64decode(base64_image)
        np_arr = np.frombuffer(image_data, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return jsonify({"error": "Invalid frame received"}), 400

        # Process the frame using BlinkDetector
        success, message, results = blink_detector.process_frame(frame)
        
        if not success:
            logger.warning(f"Detection issue: {message}")
            return jsonify({
                "error": message,
                "blink_count": results.get("blink_count", 0),
                "liveness_score": results.get("liveness_score", 0)
            }), 200
        
        # Return successful results
        logger.info(f"Processed frame: {results}")
        return jsonify({
            "status": "success",
            "message": message,
            "blink_count": results["blink_count"],
            "liveness_score": results["liveness_score"],
            "ear": results["ear"]
        })
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/reset', methods=['POST'])
def reset():
    blink_detector.reset()
    return jsonify({
        "status": "reset", 
        "blink_count": 0, 
        "liveness_score": 0
    })

if __name__ == '__main__':
    app.run(debug=True)