import subprocess
import time
import sys
import re
import json
import asyncio
import websockets

# ==============================================================================
# CONFIGURATION
# ==============================================================================
PACKAGE_NAME = "in.playsimple.escapearrow" 
APK_NAME = "app-profile.apk"
# ==============================================================================

# Global array to hold session frames
frame_history = []

def run_command(command, description):
    """Helper to run terminal commands."""
    print(f"[*] Starting: {description}...")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[!] Error during: {description}")
        print(result.stderr)
        sys.exit(1)
    return result.stdout

async def stream_performance_data(ws_url):
    """Connects to Flutter VM Service and records performance metrics."""
    global frame_history
    print(f"[*] Connecting to WebSocket: {ws_url}")
    try:
        async with websockets.connect(ws_url) as websocket:
            print("[+] Connected to Dart VM WebSocket Stream!")
            
            subscribe_request = {
                "jsonrpc": "2.0",
                "method": "streamListen",
                "params": {"streamId": "Extension"},
                "id": 1
            }
            await websocket.send(json.dumps(subscribe_request))
            print("\n" + "="*60)
            print("[*] RECORDING STARTED! Play your game now.")
            print("[*] Press Ctrl+C in this terminal when your playthrough is finished.")
            print("="*60 + "\n")

            while True:
                response = await websocket.recv()
                data = json.loads(response)
                
                if "params" in data and data["params"]["event"]["extensionKind"] == "Flutter.Frame":
                    frame_data = data["params"]["event"]["extensionData"]
                    
                    raw_ui = frame_data.get("build", frame_data.get("uiDuration", 0))
                    raw_raster = frame_data.get("raster", frame_data.get("rasterDuration", 0))
                    frame_id = frame_data.get("number", "N/A")
                    
                    ui_duration = raw_ui / 1000.0
                    raster_duration = raw_raster / 1000.0
                    total_time = ui_duration + raster_duration
                    is_jank = total_time > 16.6
                    
                    # Store data row into our runtime memory cache
                    frame_history.append({
                        "frame_id": frame_id,
                        "ui_time_ms": round(ui_duration, 2),
                        "raster_time_ms": round(raster_duration, 2),
                        "total_time_ms": round(total_time, 2),
                        "jank": is_jank
                    })
                    
                    status = "⚠️ JANK" if is_jank else "✅ OK"
                    print(f"Recorded Frame #{frame_id:<5} | UI: {ui_duration:>5.2f}ms | Raster: {raster_duration:>5.2f}ms | {status}")

    except asyncio.CancelledError:
        # Expected exit clean handling when loop task is canceled via Ctrl+C
        pass
    except Exception as e:
        print(f"[!] Stream error: {e}")

def generate_session_report():
    """Compiles analytical summaries and saves session data to JSON."""
    global frame_history
    if not frame_history:
        print("\n[!] No frame data recorded. Report generation skipped.")
        return

    total_frames = len(frame_history)
    janky_frames = sum(1 for f in frame_history if f["jank"])
    jank_percentage = (janky_frames / total_frames) * 100 if total_frames > 0 else 0
    
    avg_ui = sum(f["ui_time_ms"] for f in frame_history) / total_frames
    avg_raster = sum(f["raster_time_ms"] for f in frame_history) / total_frames
    
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "package_name": PACKAGE_NAME,
        "summary": {
            "total_frames_captured": total_frames,
            "total_janky_frames": janky_frames,
            "jank_percentage": round(jank_percentage, 2),
            "average_ui_time_ms": round(avg_ui, 2),
            "average_raster_time_ms": round(avg_raster, 2),
            "health_score": round(100 - jank_percentage, 1) # 100% health means zero jank
        },
        "frames": frame_history
    }
    
    output_filename = "performance_report.json"
    with open(output_filename, "w") as f:
        json.dump(report, f, indent=4)
        
    print("\n" + "="*60)
    print(f"[==== SESSION COMPLETED ====]")
    print(f"[+] Total Frames Processed: {total_frames}")
    print(f"[+] Overall Jank Ratio:     {report['summary']['jank_percentage']}%")
    print(f"[+] System Health Rating:   {report['summary']['health_score']}/100")
    print(f"[+] Performance JSON Written to: {output_filename}")
    print("="*60 + "\n")

def main():
    # 1. Device Handshake
    devices = run_command("adb devices", "Checking for connected Android devices")
    lines = [line for line in devices.strip().split('\n') if line]
    if len(lines) <= 1:
        print("[!] No devices detected.")
        return

    # 2. Update Application Instance
    run_command(f"adb install -r {APK_NAME}", f"Updating {APK_NAME}")
    run_command("adb logcat -c", "Clearing log caches")

    # 3. Launch Target Process
    launch_cmd = f"adb shell monkey -p {PACKAGE_NAME} -c android.intent.category.LAUNCHER 1"
    run_command(launch_cmd, "Launching game process")

    # 4. Resolve Internal Engine Tunnel Variables
    print("[*] Scanning system logs for Dart VM Service URL...")
    logcat_process = subprocess.Popen("adb logcat", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    port, auth_token = None, None
    timeout = time.time() + 30
    
    try:
        while time.time() < timeout:
            line = logcat_process.stdout.readline()
            if not line: break
            if "The Dart VM service is listening on" in line or "Observatory listening on" in line:
                match = re.search(r'http://127\.0\.0\.1:(\d+)/([^/\s]*)/', line)
                if match:
                    port = match.group(1)
                    auth_token = match.group(2)
                    break
    finally:
        logcat_process.terminate()

    if not port:
        print("[!] Timeout resolving target connectivity properties.")
        return

    # 5. Route Network Bridge maps
    run_command(f"adb forward tcp:{port} tcp:{port}", f"Establishing device bridge port mapping {port}")
    ws_url = f"ws://127.0.0.1:{port}/{auth_token}/ws"

    # 6. Execute Tracking Loop with Graceful Exit Handling
    try:
        asyncio.run(stream_performance_data(ws_url))
    except KeyboardInterrupt:
        print("\n[*] Intercepted termination directive. Wrapping up telemetry payload...")
    finally:
        generate_session_report()

if __name__ == "__main__":
    main()