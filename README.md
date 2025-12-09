# HandCameraDriver: Webcam Hand Tracking for SteamVR

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

A complete hand tracking solution using a webcam (especially optimized for PS3 Eye) to control your hands in SteamVR without physical VR controllers. Built with [SteamVR Input 2.0](https://docs.vrchat.com/docs/steamvr-input-20#hand-tracking) and MediaPipe.

Perfect for VR setups like **Cardboard + VRidge/iVRY** where you want hand tracking without expensive controllers!

## 🌟 Features

- **Real-Time Hand Tracking**: Uses MediaPipe to detect and track 21 hand landmarks per hand
- **Gesture Recognition**: Supports multiple gestures for VR interactions:
  - ✊ Fist → Grip (grab objects)
  - ☝️ Point → Trigger (click/select)
  - 🖐️ Open Hand → Release
  - 👍 Thumbs Up → Menu button
  - ✌️ Peace Sign → Teleport
  - 🤏 Pinch → Interact/Click
- **SteamVR Integration**: Custom C++ driver for seamless VR integration
- **High Performance**: Supports up to 60fps tracking (120fps with PS3 Eye at lower resolution)
- **Fully Configurable**: Extensive configuration options via `config.json`
- **Calibration System**: Built-in calibration tool for optimal tracking
- **Auto-Reconnection**: Robust socket communication with automatic reconnection

## 📋 Table of Contents

- [Hardware Requirements](#-hardware-requirements)
- [Software Requirements](#-software-requirements)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Gesture Reference](#-gesture-reference)
- [Troubleshooting](#-troubleshooting)
- [Compatibility](#-compatibility)
- [Contributing](#-contributing)
- [License](#-license)

## 🔧 Hardware Requirements

### Recommended Camera
- **PS3 Eye Camera** (Highly recommended)
  - Supports 60fps @ 640x480
  - Supports 120fps @ 320x240
  - Excellent low-light performance
  - Requires [CL Eye Driver](https://codelaboratories.com/downloads/) on Windows

### Alternative Cameras
- Any USB webcam supporting at least 30fps @ 640x480
- Phone camera via apps:
  - [Camo](https://reincubate.com/camo/) (iOS/Android)
  - [Iriun Webcam](https://iriun.com/) (iOS/Android)
  - [DroidCam](https://www.dev47apps.com/) (Android)

### PC Requirements
- **CPU**: Intel i5 / AMD Ryzen 5 or better
- **RAM**: 8GB minimum (16GB recommended)
- **OS**: Windows 10/11, Linux
- **VR Setup**: SteamVR compatible VR headset or VR bridge (VRidge, iVRY, ALVR)

## 💻 Software Requirements

### Python Environment
- Python 3.8 or higher
- pip (Python package manager)

### Required Libraries
All dependencies are listed in `requirements.txt`:
- OpenCV (opencv-python) >= 4.5.0
- MediaPipe >= 0.10.0
- NumPy >= 1.21.0

### VR Software
- **SteamVR**: Latest version
- **VR Bridge** (if using phone VR): VRidge, iVRy, or ALVR

### Build Tools (for C++ driver)
- **Windows**: Visual Studio 2019 or later with C++ tools
- **Linux**: GCC/Clang, Make
- **CMake**: 3.15 or higher

## 📦 Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/xxDMONxx/HandCameraDriverbyDmonOw.git
cd HandCameraDriverbyDmonOw
```

### Step 2: Install Python Dependencies

```bash
pip install -r requirements.txt
```

Or install manually:
```bash
pip install opencv-python mediapipe numpy
```

### Step 3: Install Camera Drivers (if using PS3 Eye)

**Windows:**
1. Download [CL Eye Driver](https://codelaboratories.com/downloads/)
2. Install and restart your computer
3. Verify camera works in CL Eye Test application

**Linux:**
```bash
# PS3 Eye is typically supported out of the box
# Verify with:
ls /dev/video*
```

### Step 4: Build and Install SteamVR Driver

**Windows:**
```bash
cd "SteamVR Driver\src"
mkdir build
cd build
cmake ..
```
Open the generated `.sln` file in Visual Studio and build the project (Release mode recommended).

**Linux:**
```bash
cd "SteamVR Driver/src"
mkdir build
cd build
cmake ..
make
```

### Step 5: Install Driver to SteamVR

**Windows:**
```bash
# Copy the driver folder to SteamVR drivers directory
xcopy /E /I "SteamVR Driver" "%ProgramFiles(x86)%\Steam\steamapps\common\SteamVR\drivers\handcameradriver"
```

**Linux:**
```bash
cp -r "SteamVR Driver" ~/.steam/steam/steamapps/common/SteamVR/drivers/handcameradriver
```

### Step 6: Enable Driver in SteamVR

1. Open SteamVR Settings
2. Go to Startup/Shutdown → Manage Add-ons
3. Enable "handcameradriver"
4. Restart SteamVR

## ⚙️ Configuration

The system is configured via `config.json`. Here's a complete reference:

### Camera Settings

```json
{
  "camera": {
    "device_id": 0,          // Camera index (0 for default camera)
    "width": 640,            // Frame width (640 or 320 for PS3 Eye)
    "height": 480,           // Frame height (480 or 240 for PS3 Eye)
    "fps": 60,               // Target FPS (60 or 120 for PS3 Eye)
    "flip_horizontal": true  // Mirror the video horizontally
  }
}
```

**PS3 Eye Configurations:**
- High Quality: 640x480 @ 60fps
- High Speed: 320x240 @ 120fps

### Tracking Settings

```json
{
  "tracking": {
    "max_hands": 2,              // Track 1 or 2 hands
    "detection_confidence": 0.7, // Higher = more strict detection
    "tracking_confidence": 0.5,  // Higher = smoother but may lose tracking
    "model_complexity": 1        // 0 (fast) or 1 (accurate)
  }
}
```

### Gesture Settings

```json
{
  "gestures": {
    "pinch_threshold": 0.05,           // Distance for pinch detection
    "finger_extended_threshold": 0.6   // Sensitivity for finger extension
  }
}
```

### Network Settings

```json
{
  "network": {
    "host": "127.0.0.1",  // Should always be localhost
    "port": 65432         // Port for communication with driver
  }
}
```

### Debug Settings

```json
{
  "debug": {
    "show_video": true,      // Display camera feed window
    "show_landmarks": true,  // Draw hand landmarks on video
    "show_fps": true,        // Display FPS counter
    "log_gestures": false    // Print gesture detection to console
  }
}
```

## 🚀 Usage

### Quick Start

1. **Start SteamVR** (make sure it's running before starting hand tracking)

2. **Run the hand tracking script:**
   ```bash
   python Camera.py
   ```

3. **Position your hands** in front of the camera (about 30-60cm away works best)

4. **Use gestures** to interact in VR!

### Calibration (Optional but Recommended)

Run the calibration tool to optimize tracking for your setup:

```bash
python calibrate.py
```

**Calibration Controls:**
- `A/D`: Adjust X offset (left/right)
- `W/S`: Adjust Y offset (up/down)
- `Q/E`: Adjust Z offset (forward/back)
- `+/-`: Adjust scale
- `R`: Reset to defaults
- `Space`: Save and exit
- `ESC`: Exit without saving

### Tips for Best Results

1. **Lighting**: Ensure good, even lighting on your hands
2. **Background**: Use a plain, non-cluttered background
3. **Distance**: Keep hands 30-60cm from camera
4. **Movement**: Start with slow movements until tracking is stable
5. **Calibration**: Run calibration if hands appear in wrong position in VR

## 🎮 Gesture Reference

| Gesture | Detection | VR Action | Trigger | Grip |
|---------|-----------|-----------|---------|------|
| **✊ Fist** | All fingers closed | Grab/Hold objects | 0.0 | 1.0 |
| **☝️ Point** | Only index finger extended | Aim/Select/Shoot | 0.8 | 0.0 |
| **🖐️ Open Hand** | All fingers extended | Release objects | 0.0 | 0.0 |
| **👍 Thumbs Up** | Only thumb extended | Menu/Button A | 0.0 | 0.0 |
| **✌️ Peace Sign** | Index + Middle extended | Teleport | 0.0 | 0.0 |
| **🤏 Pinch** | Thumb + Index touching | Precise interaction | 1.0 | 0.5 |

### Gesture Tips
- Hold gestures steady for 0.5-1 second for reliable recognition
- Practice gestures in the camera window before using in VR
- Use `log_gestures: true` in config to see real-time gesture detection

## 🔍 Troubleshooting

### Camera Issues

**Problem:** Camera not detected
- **Solution:** Check device_id in config.json (try 0, 1, 2)
- **PS3 Eye:** Ensure CL Eye Driver is installed
- **Linux:** Check permissions: `sudo usermod -a -G video $USER`

**Problem:** Low FPS / Laggy tracking
- **Solution:** 
  - Lower resolution in config.json
  - Set model_complexity to 0
  - Close other applications using camera
  - Check CPU usage

### Connection Issues

**Problem:** "Could not connect to driver"
- **Solution:**
  - Ensure SteamVR is running
  - Check driver is enabled in SteamVR settings
  - Verify port 65432 is not blocked by firewall
  - Restart SteamVR

**Problem:** Hands not showing in VR
- **Solution:**
  - Check SteamVR System Report for driver status
  - Verify hands are detected (green landmarks in camera window)
  - Try running calibration tool
  - Check SteamVR logs: `%LocalAppData%\openvr\vrserver.txt`

### Tracking Issues

**Problem:** Hands jittering or unstable
- **Solution:**
  - Increase tracking_confidence (try 0.7)
  - Improve lighting
  - Keep hands closer to camera
  - Reduce hand movement speed

**Problem:** Gestures not recognized
- **Solution:**
  - Adjust finger_extended_threshold (try 0.5-0.7)
  - Adjust pinch_threshold (try 0.03-0.08)
  - Enable log_gestures for debugging
  - Practice making gestures more distinct

### Build Issues

**Problem:** CMake configuration fails
- **Solution:**
  - Install/update CMake
  - Install Visual Studio C++ tools (Windows)
  - Install build-essential (Linux)
  - Check OpenVR SDK paths

## 🔄 Compatibility

### VR Platforms
- ✅ **SteamVR** - Full support
- ✅ **VRidge** - Compatible (phone VR)
- ✅ **iVRY** - Compatible (phone VR)
- ✅ **ALVR** - Compatible (Quest streaming)

### VR Applications
- ✅ **VRChat** - Full hand tracking support
- ✅ **Neos VR** - Compatible
- ✅ **ChilloutVR** - Compatible
- ✅ Most SteamVR games with controller input

### Operating Systems
- ✅ **Windows 10/11** - Full support
- ✅ **Linux** - Full support (Ubuntu, Arch, etc.)
- ❌ **macOS** - Not supported (OpenVR limitation)

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Areas for Contribution
- Additional gesture recognition
- Performance optimizations
- macOS support (if possible)
- Additional camera support
- Documentation improvements
- Bug fixes

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [MediaPipe](https://google.github.io/mediapipe/) - Hand tracking solution
- [OpenVR SDK](https://github.com/ValveSoftware/openvr) - SteamVR integration
- [OpenCV](https://opencv.org/) - Computer vision library
- VRChat team for SteamVR Input 2.0 support

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/xxDMONxx/HandCameraDriverbyDmonOw/issues)
- **Discussions**: [GitHub Discussions](https://github.com/xxDMONxx/HandCameraDriverbyDmonOw/discussions)

---

Made with ❤️ for the VR community. Happy hand tracking! 🖐️✨
