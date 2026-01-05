#!/usr/bin/env python3
import os
import json
import time
import subprocess
import paho.mqtt.client as mqtt
import sys
import unicodedata
from datetime import datetime

# Pomocná funkce pro logování s datem a časem
def log(message):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {message}", flush=True)

# Funkce pro bezpečné názvy témat (slug)
def slugify(text):
    text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8')
    return text.replace(" ", "_").replace("-", "_").lower()

log("--- STARTING IOT CHECKER ---")

# 1. NAČTENÍ KONFIGURACE
options_path = "/data/options.json"
try:
    with open(options_path) as f:
        config = json.load(f)
    
    # Načtení MQTT údajů a seznamu zařízení z config.yaml
    mqtt_user = config.get("mqtt_user")
    mqtt_pass = config.get("mqtt_password")
    devices = config.get("devices", [])
    
    log(f"Config read. User: {mqtt_user}")
    log(f"Number of checked devices: {len(devices)}")
except Exception as e:
    log(f"CRITICAL: Config read error: {e}")
    sys.exit(1)

# 2. DEFINICE MQTT CALLBACKŮ
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        log("SUCCESS: Connected to MQTT Broker. Registring Discovery...")
        for device in devices:
            name = device.get('name')
            if not name: continue
            safe_name = slugify(name)
            
            # Téma pro automatické nalezení v Home Assistantovi
            discovery_topic = f"homeassistant/binary_sensor/iot_checker/{safe_name}/config"
            
            payload = {
                "name": f"IoT {name}",
                "state_topic": f"iot_checker/{safe_name}/state",
                "payload_on": "online",
                "payload_off": "offline",
                "device_class": "connectivity",
                "unique_id": f"iot_checker_{safe_name}",
                "device": {
                    "identifiers": ["iot_checker_addon"],
                    "name": "IoT Network Checker",
                    "manufacturer": "ruzickav",
                    "model": "Python Ping Checker"
                }
            }
            client.publish(discovery_topic, json.dumps(payload), retain=True)
            log(f"Sensor '{name}' registered.")
    else:
        log(f"ERROR: MQTT connection error, code: {rc}")

# 3. NASTAVENÍ MQTT KLIENTA
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect

if mqtt_user and mqtt_pass:
    client.username_pw_set(mqtt_user, mqtt_pass)
    log("MQTT connection string registered.")
else:
    log("VAROVANI: MQTT username and password are empty!")

try:
    client.connect("core-mosquitto", 1883, 60)
except Exception as e:
    log(f"CRITICAL: MQTT broker (core-mosquitto) inacessible: {e}")

client.loop_start()

# 4. HLAVNÍ SMYČKA MĚŘENÍ (PING)
log("Start checking...")

last_states = {}  # Slovník pro uchování předchozího stavu

while True:
    # Oprava: Procházíme seznam 'devices' přímo, ne přes .items()
    for device in devices:
        name = device.get('name')
        ip = device.get('ip')
        
        if not name or not ip: 
            continue
            
        safe_name = slugify(name)
        
        # Ping
        res = subprocess.run(['ping', '-c', '1', '-W', '1', str(ip)], stdout=subprocess.DEVNULL)
        current_status = "online" if res.returncode == 0 else "offline"
        
        # Logujeme POUZE pokud se stav změnil
        if name not in last_states or last_states[name] != current_status:
            log(f"CHANGE: {name} ({ip}) is now {current_status}")
            last_states[name] = current_status
        
        # MQTT posíláme vždy
        client.publish(f"iot_checker/{safe_name}/state", current_status, retain=True)
        
    time.sleep(60)
