# Performance Dashboard - Flutter/Android Performance Monitor

A real-time performance monitoring and analysis dashboard for Flutter applications running on Android devices. Track frame metrics, detect jank, monitor battery health, and generate detailed performance reports with AI-powered optimization suggestions.

## 🚀 Quick Start (No Hassle)

Want to get started immediately without reading instructions? Just run:

```bash
bash run.sh
```

The script handles everything — checks prerequisites, sets up the environment, installs dependencies, and starts the server. Watch the console for the dashboard URL.

---

## Features

- 🎯 **Real-time Frame Monitoring** - Capture UI thread and raster thread metrics in real-time
- 📊 **Jank Detection** - Automatically identify frames exceeding the 16.6ms budget
- 🔋 **Battery & Thermals** - Monitor device battery level and temperature during tests
- 📈 **Interactive Dashboard** - Live visualization of performance data
- 📋 **Excel Reports** - Comprehensive performance analysis with charts and breakdowns
- 🤖 **AI-Powered Insights** - Automated suggestions for performance optimizations
- 🎮 **Event Tracking** - Correlate game events with performance spikes
- 💾 **Multiple Export Formats** - Export reports as Excel (.xlsx) or Markdown (.md)

## Prerequisites

- **Python 3.11+** (3.14+ recommended)
- **Android device** with Android 5.0+
- **ADB (Android Debug Bridge)** installed and configured
- **Flutter app** (profiling APK)

### Install ADB

**macOS (Homebrew):**
```bash
brew install android-platform-tools
```

**Linux:**
```bash
sudo apt-get install android-tools-adb
```

**Windows:**
Download from [Android SDK Platform Tools](https://developer.android.com/tools/releases/platform-tools)

## Installation

1. **Clone or download the repository:**
```bash
cd performace_dashboard
```

2. **Create virtual environment:**
```bash
python3 -m venv venv
```

3. **Activate virtual environment:**

**macOS/Linux:**
```bash
source venv/bin/activate
```

**Windows:**
```bash
venv\Scripts\activate
```

4. **Install dependencies:**
```bash
pip install -r requirements.txt
```

Or manually install:
```bash
pip install flask websockets openpyxl
```

## Quick Start

### 1. Connect Android Device

```bash
# Check connected devices
adb devices

# Enable USB debugging on your Android device (Settings → Developer Options → USB Debugging)
# Connect device via USB cable
```

### 2. Start the Dashboard Server

**Easiest (macOS/Linux):** use the run script, which sets up the virtual
environment, installs dependencies, checks for `adb`/devices, and starts the
server with helpful logs:

```bash
./run.sh
```

**Manual:**

```bash
source venv/bin/activate  # On Windows: venv\Scripts\activate
python server.py
```

The server **automatically finds a free port** (it prefers `8000`, but if that
is busy it picks another). Watch the console — it prints the exact URL, e.g.:

```
============================================================
  Performance Observability Lab
  Server running at: http://127.0.0.1:8000
  Press CTRL+C to stop
============================================================
```

To force a specific port, set the `PORT` environment variable:

```bash
PORT=8080 ./run.sh        # or: PORT=8080 python server.py
```

### 3. Open Dashboard in Browser

Navigate to the URL printed in the console (e.g. **http://127.0.0.1:8000**).

### 4. Upload & Start Test

1. Select your Flutter app's profiling APK
2. Enter the app's package name (e.g., `in.playsimple.escapearrow`)
3. Click **Start Test**
4. Play through your game/app normally
5. Click **Stop Test** when done

## Project Structure

```
performace_dashboard/
├── server.py              # Main Flask application & API endpoints
├── index.html             # Frontend dashboard UI
├── runner.py              # CLI runner for standalone performance testing
├── venv/                  # Python virtual environment
├── performance_report.json # Sample generated report
├── app-profile.apk        # Sample profiling APK (add your own)
└── README.md              # This file
```

## API Endpoints

### POST `/api/start`
Start performance monitoring session

**Parameters:**
- `package_name` (form) - Android app package name
- `apk` (file upload) - APK file to install

**Response:**
```json
{
  "success": true,
  "message": "All bulletproof layers connected live!"
}
```

### GET `/api/live`
Stream live performance data

**Query Parameters:**
- `frame_start` - Index to start reading frames (default: 0)
- `battery_start` - Index to start reading battery data (default: 0)

**Response:**
```json
{
  "active": true,
  "new_frames": [...],
  "new_battery": [...]
}
```

### POST `/api/stop`
Stop monitoring and generate report

**Response:**
```json
{
  "success": true,
  "report": {
    "timestamp": "2026-07-02 11:30:45",
    "summary": {
      "total_frames_captured": 1800,
      "total_janky_frames": 45,
      "jank_percentage": 2.5,
      "average_ui_time_ms": 8.2,
      "average_raster_time_ms": 6.1,
      "health_score": 97.5
    },
    "frames": [...],
    "battery": [...]
  }
}
```

### GET `/api/export/excel`
Download performance report as Excel file

### GET `/api/export/md`
Download performance report as Markdown file

## CLI Usage (runner.py)

For standalone monitoring without the web dashboard:

```bash
source venv/bin/activate
python runner.py
```

This will:
1. Check for connected devices
2. Install the APK specified in `PACKAGE_NAME`
3. Launch the app and capture frame data
4. Generate `performance_report.json` when interrupted (Ctrl+C)

## Understanding the Metrics

### Frame Timing
- **UI Time (ms)** - Time spent on Dart logic and widget building
- **Raster Time (ms)** - Time spent on GPU rendering (Skia)
- **Total Time (ms)** - UI Time + Raster Time
- **Jank** - Frame exceeds 16.6ms budget (causes dropped frames at 60 FPS)

### Health Score
- **100** - Perfect (0% jank)
- **90-99** - Excellent (1-10% jank)
- **80-89** - Good (11-20% jank)
- **Below 80** - Performance issues detected

### Action Spans
Execution latency tracked between two marked game events. Helps correlate specific gameplay actions with performance bottlenecks.

## Troubleshooting

### No devices detected
```bash
# Verify ADB connection
adb devices

# If device shows as "unauthorized", approve USB debugging prompt on device
adb kill-server
adb start-server
adb devices
```

### "Dart VM service" not found
- Ensure the APK is a **profiling build** (debug or profile mode)
- Release builds don't expose the Dart VM service
- Try launching the app again: go back and reopen the app

### Flask not found
```bash
# Reinstall dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Port already in use
The server auto-selects a free port, so this is rarely an issue. If you want a
specific port, set the `PORT` environment variable:

```bash
PORT=8080 ./run.sh        # or: PORT=8080 python server.py
```

To see what is occupying a given port:

```bash
lsof -i :8000
kill -9 <PID>
```

## Technologies Used

- **Backend**: Flask (Python)
- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **Real-time Data**: WebSockets (Dart VM Service)
- **Device Communication**: ADB (Android Debug Bridge)
- **Data Export**: OpenPyXL (Excel), Markdown
- **Performance Analysis**: Flutter Frame Timeline protocol

## How It Works

1. **Device Connection** - Establishes ADB connection to Android device
2. **APK Installation** - Installs profiling build of Flutter app
3. **App Launch** - Starts app and extracts Dart VM Service URL from logs
4. **Port Forwarding** - Routes Dart VM WebSocket through ADB
5. **Frame Capture** - Streams frame metrics via WebSocket in real-time
6. **Event Tracking** - Correlates app events with performance metrics
7. **Report Generation** - Compiles data into actionable insights

## Tips for Best Results

- Use a **profiling build** of your Flutter app (not release)
- Keep the **device unlocked** during tests
- Disable **background apps** to reduce noise
- Test on a **consistent device** for accurate comparisons
- Use **event markers** to correlate gameplay actions with performance
- Export reports as **Excel** for visual analysis with charts

---

**Happy Performance Hunting! 🚀**
