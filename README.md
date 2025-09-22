# Electronic Scale Project

A comprehensive electronic scale built with Raspberry Pi Pico W, featuring WiFi connectivity, web interface, MQTT integration, and power management.

## Features

- **Weight Measurement**: 0-1kg range with high accuracy (±4g)
- **Dual Units**: Switch between grams (g) and ounces (oz)
- **OLED Display**: Real-time weight display with current and last stable measurements
- **WiFi Connectivity**: Automatic connection with fallback to hotspot mode
- **Web Interface**: View, download, and manage measurements remotely
- **MQTT Integration**: Real-time data publishing to IoT platforms
- **Data Logging**: Timestamped measurements stored locally
- **Power Management**: Automatic sleep mode after 5 minutes of inactivity
- **Button Controls**: Tare function and unit switching with long-press save
- **Three-Point Calibration**: Precision calibration with 0g, 500g, and 1kg weights

## Hardware Components

| Quantity | Component | Description |
|----------|-----------|-------------|
| 1 | Raspberry Pi Pico W | Main microcontroller with WiFi |
| 1 | HX711 ADC + Load Cell | Weight sensor and amplifier |
| 1 | SSD1306 OLED Display | 128x64 pixel display |
| 2 | Push Buttons | Control interface |
| Various | Jumper Wires | Connections |



## Installation & Setup

### 1. Prepare the Raspberry Pi Pico W

1. Flash MicroPython firmware to your Pico W
2. Install required libraries via Thonny or your preferred IDE:
   - `ssd1306` (OLED display driver)
   - Built-in libraries are already included

### 2. Configure WiFi Settings

Create or modify `config.py` with your WiFi credentials:

```python
SSID = "Your_WiFi_SSID"
PSWD = "Your_WiFi_Password"

HOTSPOT_SSID = "PicoScale-WiFi"
HOTSPOT_PSWD = "scale123"
```

### 3. Wire Hardware

Connect components according to the wiring diagram.

## First Time Setup

### Initial Calibration

1. **Power on** the device
2. **Remove all weights** from the scale
3. Follow the on-screen prompts:
   - Remove all weights → Press yellow button
   - Place 500g weight → Press yellow button  
   - Place 1kg weight → Press yellow button
4. Calibration is automatically saved

### WiFi Connection

The scale will attempt to connect to your configured WiFi network. If unsuccessful within 120 seconds, it creates its own hotspot:

- **SSID**: `PicoScale-WiFi` (or your configured name)
- **Password**: `scale123` (or your configured password)
- **IP Address**: Displayed on OLED screen


## Troubleshooting

### Common Issues

#### Scale Not Reading Correctly
1. Check all wiring connections
2. Ensure stable, flat surface
3. Recalibrate the scale
4. Verify load cell is not damaged

#### WiFi Connection Problems
1. Verify credentials in `config.py`
2. Check WiFi signal strength
3. Try connecting to hotspot mode
4. Restart the device

#### Web Interface Not Accessible
1. Confirm device IP address
2. Check WiFi connection
3. Try `http://192.168.4.1` in hotspot mode
4. Disable browser cache

#### Calibration Issues
1. Use accurate reference weights
2. Ensure stable environment (no vibrations)
3. Delete `calibration.json` to force recalibration
4. Check HX711 connections

### Error Messages

- `"No calibration file found"` → Run initial calibration
- `"Sensor does not respond"` → Check HX711 wiring
- `"WiFi connection timeout"` → Device switches to hotspot mode
- `"MQTT Error"` → Check internet connection


### Recalibration
Delete `calibration.json` file and restart device to force recalibration.

