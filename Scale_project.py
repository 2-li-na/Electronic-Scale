from machine import Pin, I2C, RTC
from hx711_gpio import HX711
from ssd1306 import SSD1306_I2C
import time
import network
from wifi_module import connect, disconnect
import ntptime
import wifi_module
import config
import socket
import json
import requests
import uasyncio as asyncio
from umqtt.simple import MQTTClient 
import os


TIMEZONE_OFFSET = 1  # UTC+1:00 for CET (Central European Time)
                    # UTC+2:00 for CEST (Central European Summer Time)

# MQTT 
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_CLIENT_ID = "pico_test"
MQTT_USER = None 
MQTT_PASSWORD = None
MQTT_TOPIC = "pico_test/feeds/test"


# Init RTC
rtc = RTC()


# Print Time After Sync
print("Current Local Time:", rtc.datetime())

# Init HX711 
hx = HX711(clock=Pin(16, Pin.OUT), data=Pin(17, Pin.IN), gain=128)

# Init OLED Display
i2c = I2C(0, scl=Pin(21), sda=Pin(20), freq=400_000)
oled = SSD1306_I2C(128, 64, i2c)

# Init Buttons
btn_tare = Pin(18, Pin.IN, Pin.PULL_UP)   # --> Yellow Button
btn_unit = Pin(10, Pin.IN, Pin.PULL_UP)   # --> Black Button


# File to store data
calibration_file = "calibration.json"
log_file = "measurements.csv"

# Local variables
current_weight = 0
last_weight = 0
current_stable_weight = 0
stable_time = 10
stable_start_time = None
last_update = time.ticks_ms()
unit = "g"
timer = 300 # 5 mins in sec
weight_change = 3  # threshold
last_activity_time = time.time()
sleepmode = False
raw_500g = None
raw_1kg = None
scale_factor = None
offset = None
wifi = network.WLAN(network.STA_IF)
ap = network.WLAN(network.AP_IF)

# Global MQTT Client
client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, MQTT_PORT, MQTT_USER, MQTT_PASSWORD)


def connect_wifi():
    global wifi, ap 
    # Create Station interface
    wifi.active(True)
    print("Device IP:", network.WLAN(network.STA_IF).ifconfig()[0])
    
    oled.fill(0)
    oled.text("Connecting to", 0, 10)
    oled.text(config.SSID, 0, 25)
    oled.show()
    
    connected = wifi_module.connect(wifi, config.SSID, config.PSWD, timeout = 120)
    
    if not connected:
        ap.config(essid=config.HOTSPOT_SSID, password=config.HOTSPOT_PSWD)
        ap.active(True)
        ap_ip = ap.ifconfig()[0]
        
        oled.fill(0)
        oled.text("Hotspot:", 0, 10)
        oled.text(f"SSID: {config.HOTSPOT_SSID}", 0, 25)
        oled.text(f"PWD: {config.HOTSPOT_PSWD}", 0, 40)
        oled.show()
        
        print(f"Access Point IP: {ap_ip}")
        return False
    else:
        try:
            # Get UTC time from NTP server and set it to RTC
            ntptime.host = "pool.ntp.org"
            ntptime.settime()
            print("Time synchronized")

            # Adjust for timezone
            year, month, day, wday, hrs, mins, secs, subsecs = rtc.datetime()
            rtc.datetime((year, month, day, wday, hrs + TIMEZONE_OFFSET, mins, secs, subsecs))
        except:
            print("NTP sync failed:")
    
    return True

# MQTT Handling
async def mqtt_connect():
    try:
        print("Connecting to MQTT...")
        client.connect()
        print("MQTT Connected")
        return True
    except Exception as e:
        print("MQTT Error:", e)
        return False
    
# Save Calibration on RP2040
def save_calibration(offset, raw_500g, raw_1kg, scale_factor, unit="g"):
    data = {"offset": offset, "raw_500g": raw_500g, "raw_1kg": raw_1kg, "scale_factor": scale_factor, "unit": unit}
    with open(calibration_file, "w") as f:
        json.dump(data, f)
    print(f"Calibration Saved: {data}")

# Load Calibration from RP2040
def load_calibration():
    if calibration_file in os.listdir():
        with open(calibration_file, "r") as f:
            data = json.load(f)
            print(f"Loaded Calibration: {data}")
            return (data["offset"], data["raw_500g"], data["raw_1kg"], data["scale_factor"], data.get("unit", "g"))
    print("No calibration file found. Please calibrate!")
    return None, None, None, None, "g"

# Save measurements with timestamps
async def save_measurement(weight, unit):
    timestamp = "{:04}-{:02}-{:02} {:02}:{:02}:{:02}".format(*rtc.datetime())
    try:
        with open(log_file, "a") as f:
            f.write(f"{timestamp},{weight:.2f},{unit}\n")
            
        payload = json.dumps({
            "timestamp": timestamp,
            "value": round(weight, 2),
            "unit": unit
        })
        oled.fill(0)
        oled.text("Data Saved!", 0, 30)
        oled.show()
        client.publish(MQTT_TOPIC, payload)
        print(f"Saved Measurement: {timestamp}, {weight:.2f} {unit}\n")
        await asyncio.sleep(1)
    except Exception as e:
        print(f"MQTT-Error: {e}")
        await mqtt_connect()

def read_measurements():
    try:
        with open(log_file, "r") as f:
            lines = f.readlines()[-100:]
            return [line.strip() for line in lines]
    except:
        return []
print("Measurements: ", read_measurements())

def web_page():
    measurements = read_measurements()
    
    html = """<!DOCTYPE html>
    <html>
    <head>
        <title>Elektronische Waage</title>
        <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #2c3e50; }
        table { border-collapse: collapse; width: 100%; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background-color: #3498db; color: white; }
        tr:nth-child(even) { background-color: #f2f2f2; }
        a { 
            display: inline-block; 
            padding: 10px 20px; 
            background-color: #3498db; 
            color: white; 
            text-decoration: none; 
            border-radius: 5px;
            margin: 10px 0;
        }
        a:hover { background-color: #2980b9; }
    </style>
    </head>
    <body>
        <h1>Elektronische Waage Messungen</h1>
        <a href="/data.csv">Download CSV</a>
        <a href="/clear" style="background-color: #e74c3c;">Clear All Data</a>
        <table>
            <tr>
                <th>Timestamp</th>
                <th>Value</th>
                <th>Unit</th>
            </tr>
    """
    
    for entry in measurements:
        try:
            timestamp, value, unit = entry.strip().split(',')
            html += f"""
            <tr>
                <td>{timestamp}</td>
                <td>{value}</td>
                <td>{unit}</td>
            </tr>
            """
        except:
            continue
    
    html += """
        </table>
    </body>
    </html>
    """
    
    return html
    
# update OLED Display
def update_display(current, last, unit="g"):
    oled.fill(0)
    oled.text(f"Current:{current:.2f} {unit}", 0, 20)
    oled.text(f"Last:{last:.2f} {unit}", 0, 40)
    oled.show(0)
 

# Wait until button is pressed
def wait_for_button():
    while btn_tare.value():  
        time.sleep(0.1)

def calibrate():
    # 0g calibration
    oled.fill(0)
    oled.text("Remove all weights", 0, 10)
    oled.text("Press tare button", 0, 30)
    oled.show()
    wait_for_button()
    
    hx.tare()
    offset = hx.read_average(10)
    print(f"0g offset: {offset}")
    time.sleep(1)
    
    # 500g calibration
    oled.fill(0)
    oled.text("Place 500g weight", 0, 10)
    oled.text("Press tare button", 0, 30)
    oled.show()
    wait_for_button()
    raw_500g = hx.read_average(10)
    print(f"500g raw: {raw_500g}")
    time.sleep(1)
    
    # 1kg calibration
    oled.fill(0)
    oled.text("Place 1kg weight", 0, 10)
    oled.text("Press tare button", 0, 30)
    oled.show()
    wait_for_button()
    raw_1kg = hx.read_average(10)
    print(f"1kg raw: {raw_1kg}")
    
    # Calcuate scale factor
    scale_factor = (raw_1kg - raw_500g) / 500.0
    save_calibration(offset, raw_500g, raw_1kg, scale_factor, unit)
    return offset, scale_factor

# For Reading and maintaining the stable weight
async def read_weight():
    global current_weight, last_weight, current_stable_weight, stable_start_time, last_activity_time, sleepmode

    while True:
        current_weight = hx.get_units()
        
        # Conversion to Oz
        if unit == "oz":
            current_weight *= 0.035274
            last_weight *= 0.035274
        
        # Update display with current weight
        update_display(current_weight, last_weight, unit)
        
        # Checking weight Stability
        if abs(current_weight - current_stable_weight) <= 2:  # stable_threshod
            current_stable_weight = current_weight
            if stable_start_time is None:
                stable_start_time = time.ticks_ms()
            elif time.ticks_diff(time.ticks_ms(), stable_start_time) > stable_time * 1000:
                last_weight = current_stable_weight
                stable_start_time = None  
        else:
            current_stable_weight = current_weight
            stable_start_time = None
            
        await asyncio.sleep(0.2)
        

        
# For Both Tare and Unit Buttons and also for Sleep and wake-Up Mode    
async def handle_buttons():
    global current_weight, last_weight, last_activity_time, sleepmode, raw_500g, raw_1kg, scale_factor, offset
    
    last_tare = time.ticks_ms()
    last_unit_press = None
    
    while True:
        # Handle Unit Button
        if not btn_unit.value():  
            if last_unit_press is None:
                last_unit_press = time.ticks_ms()
        else:
            if last_unit_press is not None:  
                press_duration = time.ticks_diff(time.ticks_ms(), last_unit_press)
                
                # Short Press <1s: Toggle Units
                if press_duration < 1000:
                    global unit
                    unit = "oz" if unit == "g" else "g"
                    save_calibration(offset, raw_500g, raw_1kg, scale_factor, unit)
                    print(f"Unit switched to: {unit}")
                
                # Long Press >3s: Save Measurement
                elif press_duration > 3000: 
                    await save_measurement(current_weight, unit)
                    oled.fill(0)
                    oled.text("saved Measurement", 0, 10)
                    oled.show()
                    await asyncio.sleep(0.5)

                last_unit_press = None 
        
        # Handle tare button
        if not btn_tare.value() and time.ticks_diff(time.ticks_ms(), last_tare) > 1000:
            print("Taring...")
            hx.tare()
            offset = hx.read_average(10)
            save_calibration(offset, raw_500g, raw_1kg, scale_factor)
            last_weight = 0
            current_stable_weight = 0
            stable_start_time = None
            update_display(0, 0)
            last_tare = time.ticks_ms()
            await asyncio.sleep(0.3)
        
        # Sleep-Mode
        if abs(current_weight - last_weight) >= weight_change:
            last_activity_time = time.time()
        if not btn_tare.value() or not btn_unit.value():
            last_activity_time = time.time()
        if(time.time() - last_activity_time) > timer and not sleepmode:
            print("Entering Sleep Mode...")
            oled.fill(0)
            oled.text("Sleep Mode ON", 0, 10)
            oled.show()
            oled.poweroff()
            wifi.active(False)
            ap.active(False)     
            sleepmode = True
        
        # Wake-Up Mode
        if sleepmode and (not btn_tare.value() or not btn_unit.value()):
            print("Waking Up!")
            oled.poweron()
            wifi.active(True)
            ap.active(True)
            update_display(current_weight, last_weight, unit)
            last_activity_time = time.time()
            sleepmode = False
        
        await asyncio.sleep(0.2)

async def web_request(reader, writer):
    try:
        request = await reader.read(1024)
        request = request.decode()
        path = request.split(' ')[1] if ' ' in request else '/'

        # Route handling
        if path == '/data.csv':
            with open(log_file, 'r') as f:
                data = f.read()
                headers = (
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: text/csv\r\n"
                    f"Content-Length: {len(data)}\r\n"
                    "Content-Disposition: attachment; filename=measurements.csv\r\n\r\n"
                )
                writer.write(headers.encode())  # Sending Header as Bytes
                writer.write(data.encode())      

        elif path == '/clear':
            # Clear data
            open(log_file, 'w').close()
            html_response = "<h1 style='color: #e74c3c;'>All measurements cleared!</h1>"
            headers = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/html\r\n"
                f"Content-Length: {len(html_response)}\r\n\r\n"
            )
            writer.write(headers.encode())
            writer.write(html_response.encode())

        else:
            # Show basic HTML
            html = web_page()
            headers = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/html\r\n"
                f"Content-Length: {len(html)}\r\n\r\n"
            )
            writer.write(headers.encode())
            writer.write(html.encode())  
        
        await writer.drain()
        writer.close()
    
    except Exception as e:
        print(f"Error in web_request: {e}")
    
async def web_server():
    server = await asyncio.start_server(web_request, "0.0.0.0", 80)
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        server.close()
        await server.wait_closed()
        
#--------------------------------------------------------
async def main():
    global offset, raw_500g, raw_1kg, scale_factor, unit
    
    offset, raw_500g, raw_1kg, scale_factor, unit = load_calibration()
    if None in (offset, scale_factor):
        offset, scale_factor = calibrate()
        
    connect_wifi()
    await mqtt_connect()
    
    hx.set_offset(offset)
    hx.set_scale(scale_factor)
    print("\nStarting measurements...")
    print(f"Calibration values - Offset: {offset}, Scale: {scale_factor}")
    
    server_task = asyncio.create_task(web_server())
    await asyncio.gather(
        read_weight(),
        handle_buttons(),
        server_task
        )

try:
    asyncio.run(main())

except KeyboardInterrupt:
    oled.fill(0)  
    oled.show()   
    print("\nOLED turned off. Program stopped.")


