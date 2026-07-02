from flask import Flask, request, jsonify, render_template
import subprocess
import time
import re
import json
import threading
import os
from websockets.sync.client import connect
from websockets.exceptions import ConnectionClosed

app = Flask(__name__, template_folder='.', static_folder='.', static_url_path='')

# Global configurations and states
UPLOAD_FOLDER = os.path.dirname(os.path.abspath(__file__))
frame_history = []
tracking_active = False

def run_command(command):
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        return False, result.stderr
    return True, result.stdout

def stream_performance_data(ws_url):
    global frame_history, tracking_active
    try:
        with connect(ws_url) as websocket:
            subscribe_request = {
                "jsonrpc": "2.0",
                "method": "streamListen",
                "params": {"streamId": "Extension"},
                "id": 1
            }
            websocket.send(json.dumps(subscribe_request))

            while tracking_active:
                try:
                    response = websocket.recv(timeout=1.0)
                    data = json.loads(response)

                    if "params" in data and data["params"]["event"]["extensionKind"] == "Flutter.Frame":
                        frame_data = data["params"]["event"]["extensionData"]
                        raw_ui = frame_data.get("build", frame_data.get("uiDuration", 0))
                        raw_raster = frame_data.get("raster", frame_data.get("rasterDuration", 0))

                        frame_history.append({
                            "frame_id": frame_data.get("number", "N/A"),
                            "ui_time_ms": round(raw_ui / 1000.0, 2),
                            "raster_time_ms": round(raw_raster / 1000.0, 2),
                            "total_time_ms": round((raw_ui + raw_raster) / 1000.0, 2),
                            "jank": ((raw_ui + raw_raster) / 1000.0) > 16.6
                        })
                except TimeoutError:
                    continue
    except ConnectionClosed:
        pass
    except Exception as e:
        print(f"WebSocket Error: {e}")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/start', methods=['POST'])
def start_test():
    global frame_history, tracking_active

    package_name = request.form.get('package_name')
    apk_file = request.files.get('apk')

    if not package_name or not apk_file:
        return jsonify({"success": False, "error": "Missing package name or APK file."}), 400

    frame_history = []
    tracking_active = True

    apk_path = os.path.join(UPLOAD_FOLDER, "temp-target-profile.apk")
    apk_file.save(apk_path)

    success, devices = run_command("adb devices")
    if not success or len([l for l in devices.strip().split('\n') if l]) <= 1:
        return jsonify({"success": False, "error": "No USB devices detected by ADB."})

    success, err = run_command(f"adb install -r {apk_path}")
    if not success:
        return jsonify({"success": False, "error": f"Installation failed: {err}"})

    run_command("adb logcat -c")

    launch_cmd = f"adb shell monkey -p {package_name} -c android.intent.category.LAUNCHER 1"
    success, err = run_command(launch_cmd)
    if not success:
        return jsonify({"success": False, "error": f"Launch failed: {err}"})

    logcat_process = subprocess.Popen(
        "adb logcat", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    port, auth_token = None, None
    timeout = time.time() + 20

    while time.time() < timeout:
        line = logcat_process.stdout.readline()
        if "The Dart VM service is listening on" in line or "Observatory listening on" in line:
            match = re.search(r'http://127\.0\.0\.1:(\d+)/([^/\s]*)/', line)
            if match:
                port = match.group(1)
                auth_token = match.group(2)
                break
    logcat_process.terminate()

    if not port:
        return jsonify({"success": False, "error": "Could not extract Dart VM link. Ensure it's a Profile-mode APK."})

    run_command(f"adb forward tcp:{port} tcp:{port}")
    ws_url = f"ws://127.0.0.1:{port}/{auth_token}/ws"

    threading.Thread(target=stream_performance_data, args=(ws_url,), daemon=True).start()
    return jsonify({"success": True, "message": "Session tracking started successfully!"})

@app.route('/api/stop', methods=['POST'])
def stop_test():
    global tracking_active, frame_history
    tracking_active = False

    if not frame_history:
        return jsonify({"success": False, "error": "No telemetry captured during session."})

    total_frames = len(frame_history)
    janky_frames = sum(1 for f in frame_history if f["jank"])
    jank_percentage = (janky_frames / total_frames) * 100 if total_frames > 0 else 0
    avg_ui = sum(f["ui_time_ms"] for f in frame_history) / total_frames
    avg_raster = sum(f["raster_time_ms"] for f in frame_history) / total_frames

    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "total_frames_captured": total_frames,
            "total_janky_frames": janky_frames,
            "jank_percentage": round(jank_percentage, 2),
            "average_ui_time_ms": round(avg_ui, 2),
            "average_raster_time_ms": round(avg_raster, 2),
            "health_score": round(100 - jank_percentage, 1)
        },
        "frames": frame_history
    }

    return jsonify({"success": True, "report": report})

if __name__ == '__main__':
    app.run(port=5000, debug=True)
