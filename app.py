import os
import cv2
import requests
import psutil
from flask import Flask, Response, render_template_string, send_from_directory

app = Flask(__name__)

# --- LINE Notification Setup ---
LINE_ACCESS_TOKEN = os.environ.get("LINE_ACCESS_TOKEN", "")
SAVE_DIR = "captured_images"

if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

def send_line_message(message):
    if not LINE_ACCESS_TOKEN:
        return
    url = 'https://notify-api.line.me/api/notify'
    headers = {'Authorization': f'Bearer {LINE_ACCESS_TOKEN}'}
    data = {'message': message}
    try:
        requests.post(url, headers=headers, data=data)
    except Exception as e:
        print(f"Error sending LINE alert: {e}")

# --- Video Stream Generator ---
def generate_frames():
    droidcam_url = "http://192.168.1.151:4747/video"
    camera = cv2.VideoCapture(droidcam_url)
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

# --- Liquid Glass Styled HTML Template ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="th" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VLDAR Bot Dashboard</title>
    <style>
        :root[data-theme="dark"] {
            --bg-color: #050608;
            --card-bg: rgba(255, 255, 255, 0.03);
            --card-border: rgba(255, 255, 255, 0.08);
            --text-color: #ffffff;
            --text-muted: rgba(255, 255, 255, 0.6);
            --accent-color: #007aff;
            --success-color: #34c759;
            --sidebar-bg: rgba(255, 255, 255, 0.02);
            --warning-color: #ff9500;
        }
        :root[data-theme="light"] {
            --bg-color: #f2f5f8;
            --card-bg: rgba(255, 255, 255, 0.6);
            --card-border: rgba(0, 0, 0, 0.05);
            --text-color: #1c1c1e;
            --text-muted: rgba(0, 0, 0, 0.5);
            --accent-color: #007aff;
            --success-color: #34c759;
            --sidebar-bg: rgba(255, 255, 255, 0.4);
            --warning-color: #ff9500;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            padding: 0;
            display: flex;
            transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
            background-image: radial-gradient(at 0% 0%, rgba(0, 122, 255, 0.05) 0px, transparent 50%),
                              radial-gradient(at 100% 0%, rgba(52, 199, 89, 0.05) 0px, transparent 50%);
            min-height: 100vh;
        }
        /* Sidebar */
        .sidebar {
            width: 260px;
            background-color: var(--sidebar-bg);
            backdrop-filter: blur(20px) saturate(180%);
            border-right: 1px solid var(--card-border);
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 20px;
            transition: transform 0.3s ease;
            position: relative;
            z-index: 10;
        }
        .sidebar-header {
            font-size: 1.25rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            justify-content: space-between;
            letter-spacing: -0.5px;
        }
        .menu-btn {
            background: none;
            border: none;
            color: var(--text-color);
            font-size: 1.5rem;
            cursor: pointer;
        }
        .nav-links {
            list-style: none;
            padding: 0;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .nav-links a {
            color: var(--text-color);
            text-decoration: none;
            padding: 12px 16px;
            border-radius: 12px;
            transition: all 0.2s;
            font-weight: 500;
            backdrop-filter: blur(5px);
        }
        .nav-links a:hover {
            background-color: rgba(255, 255, 255, 0.05);
        }
        /* Main Content */
        .main-content {
            flex: 1;
            padding: 24px;
            display: flex;
            flex-direction: column;
            gap: 20px;
            max-width: calc(100% - 260px);
            position: relative;
            z-index: 1;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header h2 {
            font-size: 1.75rem;
            font-weight: 800;
            letter-spacing: -0.5px;
            margin: 0;
        }
        .theme-btn, .line-btn {
            background: var(--card-bg);
            backdrop-filter: blur(20px) saturate(180%);
            color: var(--text-color);
            border: 1px solid var(--card-border);
            padding: 10px 20px;
            border-radius: 14px;
            cursor: pointer;
            transition: all 0.2s;
            font-weight: 600;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.02);
        }
        .theme-btn:hover, .line-btn:hover {
            background-color: rgba(255, 255, 255, 0.1);
            transform: translateY(-1px);
        }
        .actions {
            display: flex;
            gap: 12px;
        }
        /* Grid Layout */
        .grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
        }
        .card {
            background: var(--card-bg);
            backdrop-filter: blur(20px) saturate(180%);
            border: 1px solid var(--card-border);
            border-radius: 28px;
            padding: 24px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        .card::before {
            content: '';
            position: absolute;
            top: 0; left: 0; width: 100%; height: 100%;
            border-radius: inherit;
            padding: 1px;
            background: linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0) 100%);
            -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
            mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
            -webkit-mask-composite: xor;
            mask-composite: exclude;
            pointer-events: none;
        }
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.12);
        }
        .card-large {
            grid-column: span 2;
        }
        .card-wide {
            grid-column: span 3;
        }
        .video-feed {
            width: 100%;
            border-radius: 20px;
            background: #000;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }
        h3 {
            margin-top: 0;
            font-size: 1.1rem;
            color: var(--text-muted);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .status-badge {
            display: inline-block;
            padding: 6px 14px;
            border-radius: 12px;
            background: var(--success-color);
            color: #ffffff;
            font-size: 0.85rem;
            font-weight: 700;
            box-shadow: 0 4px 12px rgba(52, 199, 89, 0.3);
        }
        .warning-badge {
            background: var(--warning-color);
            box-shadow: 0 4px 12px rgba(255, 149, 0, 0.3);
        }
        /* Progress Bar */
        .progress-container {
            width: 100%;
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            height: 12px;
            overflow: hidden;
            margin: 12px 0;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
        }
        .progress-bar {
            height: 100%;
            border-radius: 10px;
            background: linear-gradient(90deg, var(--accent-color), #5856d6);
            transition: width 0.5s ease;
        }
        /* Gallery */
        .gallery {
            display: flex;
            gap: 12px;
            overflow-x: auto;
            padding: 10px 0;
        }
        .gallery::-webkit-scrollbar {
            height: 8px;
        }
        .gallery::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
        }
        .gallery img {
            height: 120px;
            border-radius: 16px;
            border: 1px solid var(--card-border);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }
        .gallery img:hover {
            transform: scale(1.05);
        }
        /* Footer Status & Controls */
        .footer-section {
            background: var(--card-bg);
            backdrop-filter: blur(20px) saturate(180%);
            border: 1px solid var(--card-border);
            border-radius: 28px;
            padding: 24px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
            margin-top: auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .control-panel {
            display: flex;
            gap: 15px;
            align-items: center;
            background: rgba(0, 0, 0, 0.1);
            padding: 8px 16px;
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }
        .control-btn {
            background: var(--accent-color);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 14px;
            cursor: pointer;
            font-weight: 700;
            transition: all 0.2s;
            box-shadow: 0 4px 12px rgba(0, 122, 255, 0.3);
        }
        .control-btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 16px rgba(0, 122, 255, 0.4);
        }
    </style>
</head>
<body>
    <!-- Sidebar -->
    <nav class="sidebar" id="sidebar">
        <div class="sidebar-header">
            <span>VLDAR Panel</span>
            <button class="menu-btn" onclick="toggleSidebar()">☰</button>
        </div>
        <ul class="nav-links">
            <li><a href="#">Dashboard</a></li>
            <li><a href="#">Settings</a></li>
        </ul>
    </nav>

    <!-- Main Content -->
    <main class="main-content">
        <div class="header">
            <h2>VLDAR Bot Dashboard</h2>
            <div class="actions">
                <a href="https://line.me/R/ti/p/@your_line_id" class="line-btn" target="_blank">➕ เพิ่มเพื่อน LINE</a>
                <button class="theme-btn" onclick="toggleTheme()">🌓 สลับธีม</button>
            </div>
        </div>

        <div class="grid">
            <!-- Camera Feed -->
            <div class="card card-large">
                <h3>Camera Feed (Live)</h3>
                <img src="/video_feed" class="video-feed" alt="Live Stream">
            </div>

            <!-- System Status -->
            <div class="card">
                <h3>System Status</h3>
                <p>Status: <span class="status-badge">ONLINE</span></p>
                <p>Detection: Active</p>
                <p>LINE Notify: Connected</p>
                <h3>Task Queue</h3>
                <p>Current Task: Monitoring</p>
                <p>Queue Length: 0</p>
            </div>

            <!-- Battery Level -->
            <div class="card">
                <h3>Battery Level</h3>
                <div style="font-size: 2.5rem; font-weight: 800; margin: 10px 0;">88%</div>
                <div class="progress-container">
                    <div class="progress-bar" style="width: 88%;"></div>
                </div>
            </div>

            <!-- System Health -->
            <div class="card">
                <h3>System Health</h3>
                <div style="margin-bottom: 20px;">
                    <p style="margin: 0; font-size: 0.9rem; font-weight: 600;">CPU Usage: {{ cpu_percent }}%</p>
                    <div class="progress-container">
                        <div class="progress-bar" style="width: {{ cpu_percent }}%;"></div>
                    </div>
                </div>
                <div>
                    <p style="margin: 0; font-size: 0.9rem; font-weight: 600;">Memory Usage: {{ mem_percent }}%</p>
                    <div class="progress-container">
                        <div class="progress-bar" style="width: {{ mem_percent }}%;"></div>
                    </div>
                </div>
            </div>

            <!-- Captured Images -->
            <div class="card card-wide">
                <h3>Last Captured Images</h3>
                <div class="gallery">
                    {% for img in images %}
                        <img src="/images/{{ img }}" alt="Captured">
                    {% else %}
                        <p style="color: var(--text-muted);">ไม่มีรูปภาพที่บันทึกไว้</p>
                    {% endfor %}
                </div>
            </div>
        </div>

        <!-- Footer Status & Controls -->
        <div class="footer-section">
            <div>
                <h3>System Logs & Status</h3>
                <p style="margin: 0; font-weight: 500;">VLDAR Bot (DroidCam + Detection + Save Image + LINE) is running!</p>
                <p style="margin: 10px 0 0 0;">ระบบขับเคลื่อน: <span class="status-badge warning-badge">Coming Soon</span></p>
            </div>
            <div class="control-panel">
                <h3 style="margin: 0; color: var(--text-color);">ระบบควบคุม</h3>
                <button class="control-btn">Start</button>
                <button class="control-btn" style="background: rgba(255, 255, 255, 0.1); box-shadow: none; color: var(--text-color);">Stop</button>
            </div>
        </div>
    </main>

    <script>
        function toggleTheme() {
            const html = document.documentElement;
            const current = html.getAttribute('data-theme');
            html.setAttribute('data-theme', current === 'dark' ? 'light' : 'dark');
        }
        function toggleSidebar() {
            const sidebar = document.getElementById('sidebar');
            sidebar.style.transform = sidebar.style.transform === 'translateX(-100%)' ? 'translateX(0)' : 'translateX(-100%)';
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory().percent
    images = sorted(os.listdir(SAVE_DIR), reverse=True)[:10]
    return render_template_string(HTML_TEMPLATE, cpu_percent=cpu, mem_percent=mem, images=images)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/images/<filename>')
def get_image(filename):
    return send_from_directory(SAVE_DIR, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
