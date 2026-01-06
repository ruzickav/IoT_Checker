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

# Pomocná funkce pro logování
def log(message):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {message}", flush=True)

# Funkce pro bezpečné názvy témat (slug)
def slugify(text):
    text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8')
    return text.replace(" ", "_").replace("-", "_").lower()

log("--- SPUSTENI PARALELNIHO IOT CHECKERU v1.5.0 ---")

# 1. NAČTENÍ KONFIGURACE
options_path = "/data/options.json"
try:
    with open(options_path) as f:
        config = json.load(f)
    mqtt_user = config.get("mqtt_user")
    mqtt_pass = config.get("mqtt_password")
    devices_list = config.get("devices", [])
    log(f"Konfigurace nactena. Pocet zarizeni: {len(devices_list)}")
except Exception as e:
    log(f"CRITICAL: Chyba pri cteni konfigurace: {e}")
    sys.exit(1)

# 2. MQTT NASTAVENÍ
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        log("SUCCESS: Pripojeno k MQTT. Registruji Discovery...")
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
        log(f"ERROR: MQTT chyba pripojeni: {rc}")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
if mqtt_user and mqtt_pass:
    client.username_pw_set(mqtt_user, mqtt_pass)

try:
    client.connect("core-mosquitto", 1883, 60)
except Exception as e:
    log(f"CRITICAL: MQTT nedostupny: {e}")

client.loop_start()

# 3. FUNKCE PRO JEDEN PING (Běží v samostatném vlákně)
def check_device(device):
    name = device.get('name')
    ip = device.get('ip')
    if not name or not ip: return None

    # Tady je tvůj upravený ping bez -W
    res = subprocess.run(['ping', '-c', '3', str(ip)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    status = "online" if res.returncode == 0 else "offline"
    
    return {"name": name, "ip": ip, "status": status}

# 4. HLAVNÍ SMYČKA
last_states = {}

while True:
    start_time = time.time()
    
    # Spustíme pingy paralelně pro všechna zařízení najednou
    with ThreadPoolExecutor(max_workers=50) as executor:
        results = list(executor.map(check_device, devices_list))

    # Zpracujeme výsledky
    for res in results:
        if res is None: continue
        
        name = res['name']
        status = res['status']
        safe_name = slugify(name)

        # Logujeme jen změny
        if name not in last_states or last_states[name] != status:
            log(f"ZMENA: {name} ({res['ip']}) je nyni {status}")
            last_states[name] = status
        
        # MQTT posíláme vždy
        client.publish(f"iot_checker/{safe_name}/state", status, retain=True)

    duration = time.time() - start_time
    log(f"Kolo mereni dokonceno za {duration:.2f} s. Cekam na dalsi kolo...")
    
    time.sleep(60)
