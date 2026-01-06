#!/usr/bin/env python3
import os
import json
import time
import subprocess
import paho.mqtt.client as mqtt
import sys
import unicodedata
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# Logovací funkce s časovou značkou
def log(message):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {message}", flush=True)

# Funkce pro slugify (převod jmen na ID)
def slugify(text):
    text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8')
    return text.replace(" ", "_").replace("-", "_").lower()

log("--- STARTING PARALLEL IOT CHECKER v1.5.1 ---")

# 1. LOAD CONFIGURATION
options_path = "/data/options.json"
try:
    with open(options_path) as f:
        config = json.load(f)
    mqtt_user = config.get("mqtt_user")
    mqtt_pass = config.get("mqtt_password")
    devices_list = config.get("devices", [])
    log(f"Configuration loaded. Monitoring {len(devices_list)} devices.")
except Exception as e:
    log(f"CRITICAL ERROR: Failed to load configuration: {e}")
    sys.exit(1)

# 2. MQTT CALLBACKS
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        log("SUCCESS: Connected to MQTT broker. Registering Discovery...")
        for dev in devices_list:
            name = dev.get('name')
            if not name: continue
            safe_name = slugify(name)
            discovery_topic = f"homeassistant/binary_sensor/iot_checker/{safe_name}/config"
            payload = {
                "name": f"IoT {name}",
                "state_topic": f"iot_checker/{safe_name}/state",
                "payload_on": "online",
                "payload_off": "offline",
                "device_class": "connectivity",
                "unique_id": f"iot_checker_{safe_name}"
            }
            client.publish(discovery_topic, json.dumps(payload), retain=True)
    else:
        log(f"ERROR: MQTT connection failed with code: {rc}")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
if mqtt_user and mqtt_pass:
    client.username_pw_set(mqtt_user, mqtt_pass)

try:
    client.connect("core-mosquitto", 1883, 60)
except Exception as e:
    log(f"CRITICAL ERROR: MQTT broker unreachable: {e}")

client.loop_start()

# 3. PING FUNCTION (Runs in worker threads)
def check_device(device):
    name = device.get('name')
    ip = device.get('ip')
    if not name or not ip: return None

    # Ping command with 3 packets
    res = subprocess.run(['ping', '-c', '3', str(ip)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    status = "online" if res.returncode == 0 else "offline"
    
    return {"name": name, "ip": ip, "status": status}

# 4. MAIN LOOP
log("Device monitoring started...")
last_states = {}

while True:
    start_time = time.time()
    
    # Execute pings in parallel
    with ThreadPoolExecutor(max_workers=50) as executor:
        results = list(executor.map(check_device, devices_list))

    # Process results
    for res in results:
        if res is None: continue
        
        name = res['name']
        status = res['status']
        safe_name = slugify(name)

        # Log changes only
        if name not in last_states or last_states[name] != status:
            log(f"STATE CHANGE: {name} ({res['ip']}) is now {status}")
            last_states[name] = status
        
        # Always publish state to MQTT
        client.publish(f"iot_checker/{safe_name}/state", status, retain=True)

    duration = time.time() - start_time
    log(f"Scan cycle completed in {duration:.2f} seconds. Sleeping for 60s...")
    
    time.sleep(60)
