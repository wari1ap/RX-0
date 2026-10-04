import os
import time
import requests
import cv2
from flask import Flask, Response, render_template_string, request, jsonify

app = Flask(__name__)

# ==========================================
# Configuration (ดึงค่าจาก Environment Variables)
# ==========================================
# IP และ RTSP URL สำหรับกล้อง Smart Life (ใช้ IP: 192.168.1.140)
CAMERA_IP = os.getenv("CAMERA_IP", "192.168.1.140")
CAMERA_USER = os.getenv("CAMERA_USER", "admin")
CAMERA_PASS = os.getenv("CAMERA_PASS", "admin") # เปลี่ยนเป็น Password ของกล้องที่คุณตั้งในแอป Smart Life
RTSP_URL = os.getenv("RTSP_URL", f"rtsp://{CAMERA_USER}:{CAMERA_PASS}@{CAMERA_IP}:554/live/ch0")

# LINE Notify Token (ใส่ Token ของคุณเป็นค่า Default ไว้ให้แล้ว)
LINE_NOTIFY_TOKEN = os.getenv(
    "LINE_NOTIFY_TOKEN",
    "jnlApIVgKhlzKwr+VrcJ5qTrb7z3pS0PuGFoHAj9Is3J++VGcUCQBiDK+qctLF+wSAmeQQ+gxwOpSNhCFSctSYf0lQX0HwMLxYfCWY7lvAvled5mxpKu56vdhTrLc+jwQ85FoEPWsgZCHFALoeWwYwdB04t89/1O/w1cDnyilFU="
)

# ==========================================
# Helper Functions
# ==========================================
def send_line_notify(message: str) -> bool:
    """ฟังก์ชันส่งข้อความแจ้งเตือนไปยัง LINE Notify"""
    url = "https://notify-api.line.me/api/notify"
    headers = {"Authorization": f"Bearer {LINE_NOTIFY_TOKEN}"}
    data = {"message": message}
    try:
        response = requests.post(url, headers=headers, data=data, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"Failed to send LINE notification: {e}")
        return False

def generate_frames():
    """ฟังก์ชันดึงภาพวิดีโอสดจากกล้องวงจรปิดผ่าน RTSP"""
    camera = cv2.VideoCapture(RTSP_URL)
    while True:
        success, frame = camera.read()
        if not success:
            time.sleep(0.5)
            camera = cv2.VideoCapture(RTSP_URL)
            continue
        else:
            # ย่อขนาดภาพให้พอดีกับการแสดงผลบนหน้าเว็บ
            frame = cv2.resize(frame, (640, 480))
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

# ==========================================
# Web Routes & HTML Interface
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Robot & Smart Life Camera Control Center</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #121212; color: #fff; margin: 0; padding: 20px; text-align: center; }
        h1 { color: #00adb5; margin-bottom: 20px; }
        .container { max-width: 900px; margin: 0 auto; background: #1e1e1e; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
        .video-card { background: #000; border-radius: 8px; overflow: hidden; display: inline-block; border: 2px solid #333; margin-bottom: 20px; }
        .video-card img { width: 100%; max-width: 640px; height: auto; display: block; }
        .controls { display: grid; grid-template-columns: repeat(3, 80px); gap: 10px; justify-content: center; margin: 15px auto; }
        .btn { padding: 15px; font-size: 18px; font-weight: bold; background: #393e46; color: #eeeeee; border: none; border-radius: 8px; cursor: pointer; transition: 0.2s; }
        .btn:hover { background: #00adb5; color: #fff; }
        .btn-up { grid-column: 2; }
        .btn-left { grid-column: 1; grid-row: 2; }
        .btn-stop { grid-column: 2; grid-row: 2; background: #e63946; }
        .btn-right { grid-column: 3; grid-row: 2; }
        .btn-down { grid-column: 2; grid-row: 3; }
        .action-area { margin-top: 25px; padding-top: 15px; border-top: 1px solid #333; }
        .btn-notify { background: #06c755; color: white; padding: 12px 24px; font-size: 16px; font-weight: bold; border: none; border-radius: 6px; cursor: pointer; }
        .btn-notify:hover { background: #05b34c; }
        #status-msg { margin-top: 10px; font-size: 14px; color: #00adb5; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Robot Control & Smart Life Camera Center</h1>
        
        <!-- Live Camera Stream -->
        <div class="video-card">
            <img src="{{ url_for('video_feed') }}" alt="Smart Life Camera Feed (192.168.1.140)">
        </div>

        <!-- Robot Movement Controls -->
        <div>
            <h3>การควบคุมหุ่นยนต์ (Robot Movement)</h3>
            <div class="controls">
                <button class="btn btn-up" onclick="sendCommand('FORWARD')">▲</button>
                <button class="btn btn-left" onclick="sendCommand('LEFT')">◀</button>
                <button class="btn btn-stop" onclick="sendCommand('STOP')">■</button>
                <button class="btn btn-right" onclick="sendCommand('RIGHT')">▶</button>
                <button class="btn btn-down" onclick="sendCommand('BACKWARD')">▼</button>
            </div>
        </div>

        <!-- LINE Notification Section -->
        <div class="action-area">
            <h3>ระบบแจ้งเตือน (LINE Notification)</h3>
            <button class="btn-notify" onclick="sendAlert()">🔔 ส่งการแจ้งเตือนไปยัง LINE</button>
            <div id="status-msg"></div>
        </div>
    </div>

    <script>
        function sendCommand(cmd) {
            console.log("Sending Command:", cmd);
            fetch('/control', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: cmd })
            });
        }

        function sendAlert() {
            document.getElementById('status-msg').innerText = "กำลังส่งแจ้งเตือน...";
            fetch('/notify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: "🤖 หุ่นยนต์ทำงานปกติ! ตรวจสอบกล้อง Smart Life (192.168.1.140)" })
            })
            .then(res => res.json())
            .then(data => {
                document.getElementById('status-msg').innerText = data.status === 'success' 
                    ? "✅ ส่งการแจ้งเตือน LINE เรียบร้อยแล้ว!" 
                    : "❌ การส่งแจ้งเตือนล้มเหลว";
            });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/control', methods=['POST'])
def control():
    data = request.get_json() or {}
    command = data.get('command', 'STOP')
    print(f"Received robot command: {command}")
    # สามารถเพิ่มโค้ดสั่งงานฮาร์ดแวร์หุ่นยนต์จริง (เช่น GPIO / Serial) ได้ที่นี่
    return jsonify({"status": "success", "command": command})

@app.route('/notify', methods=['POST'])
def notify():
    data = request.get_json() or {}
    message = data.get('message', 'Alert from Robot System')
    success = send_line_notify(message)
    return jsonify({"status": "success" if success else "failed"})

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
