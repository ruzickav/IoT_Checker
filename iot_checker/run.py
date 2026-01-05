#!/usr/bin/env python3
import os
import json
import time
import subprocess
import paho.mqtt.client as mqtt
import sys
from datetime import datetime

# Pomocná funkce pro logování s datem a časem
def log(message):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {message}", flush=True)

log("--- SPUSTENI IOT CHECKERU ---")

# 1. NAČTENÍ KONFIGURACE
options_path = "/data/options.json"
try:
    with open(options_path) as f:
        config = json.load(f)
    
    # Načtení MQTT údajů a seznamu zařízení z config.yaml
    mqtt_user = config.get("mqtt_user")
    mqtt_pass = config.get("mqtt_password")
    devices = config.get("devices", [])
    
    log(f"Konfigurace nactena. Uzivatel: {mqtt_user}")
    log(f"Pocet sledovanych zarizeni: {len(devices)}")
except Exception as e:
    log(f"CRITICAL: Chyba pri cteni konfigurace: {e}")
    sys.exit(1)

# 2. DEFINICE MQTT CALLBACKŮ
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        log("SUCCESS: Pripojeno k MQTT brokeru. Registruji Discovery...")
        for device in devices:
            name = device.get('name')
            safe_name = name.replace(" ", "_").lower()
            
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
                    "manufacturer": "Moje HA Dilna",
                    "model": "Python Ping Checker"
                }
            }
            client.publish(discovery_topic, json.dumps(payload), retain=True)
            log(f"Senzor '{name}' zaregistrovan.")
    else:
        # Kód 5 znamená, že jméno nebo heslo nesouhlasí
        log(f"ERROR: MQTT chyba pripojeni, kod: {rc} (5 = neautorizovano)")

# 3. NASTAVENÍ MQTT KLIENTA
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect

# Použití údajů zadaných v kartě Nastavení u doplňku
if mqtt_user and mqtt_pass:
    client.username_pw_set(mqtt_user, mqtt_pass)
    log("MQTT prihlasovaci udaje nastaveny.")
else:
    log("VAROVANI: MQTT udaje v konfiguraci jsou prazdne!")

try:
    # Připojení na vnitřní síť Home Assistanta
    client.connect("core-mosquitto", 1883, 60)
except Exception as e:
    log(f"CRITICAL: MQTT broker (core-mosquitto) nedostupny: {e}")

# Spuštění MQTT procesů na pozadí
client.loop_start()

# 4. HLAVNÍ SMYČKA MĚŘENÍ (PING)
log("Zacinam merit dostupnost...")

while True:
    for device in devices:
        ip = device.get('ip')
        name = device.get('name')
        
        if not ip or not name:
            continue
            
        safe_name = name.replace(" ", "_").lower()
        
        # Provedení pingu (1 pokus, timeout 1 sekunda)
        res = subprocess.run(['ping', '-c', '1', '-W', '1', ip], stdout=subprocess.DEVNULL)
        status = "online" if res.returncode == 0 else "offline"
        
        # Odeslání stavu do MQTT tématu pro konkrétní zařízení
        state_topic = f"iot_checker/{safe_name}/state"
        client.publish(state_topic, status, retain=True)
        
        log(f"Ping: {name} ({ip}) -> {status}")
        
    # Počkáme 60 sekund před dalším kolem měření
    time.sleep(60)