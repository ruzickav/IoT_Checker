My simple addon for Home Assistant

# IoT Network Checker Add-on Repository

Welcome to my Home Assistant add-on repository! This add-on allows you to monitor the availability of various devices in your local network using ICMP ping.

## 🚀 Add-on: IoT Network Checker

A lightweight tool that pings your network devices and reports their status (online/offline) directly to Home Assistant via MQTT.

### Features
- **Auto-Discovery**: Automatically creates binary sensors in Home Assistant.
- **Connectivity Class**: Uses native Home Assistant device classes for beautiful icons and state colors.
- **Fast & Lightweight**: Efficiently handles dozens of devices in a single loop.
- **Customizable**: Easy configuration via a simple list of names and IP addresses.

---

## 📦 Installation

To add this repository to your Home Assistant instance:

1. Copy the URL of this GitHub repository.
2. In Home Assistant, go to **Settings** -> **Add-ons**.
3. Click on **Add-on Store** (bottom right).
4. Click the **three dots** in the top right corner and select **Repositories**.
5. Paste the URL ( https://github.com/ruzickav/IoT_Checker ) and click **Add**.
6. You will now see "IoT Network Checker" under the local/private section. Click it and select **Install**.

---

## ⚙️ Configuration

Once installed, go to the **Configuration** tab. You can use the UI or switch to YAML mode (recommended for many devices).

### Example YAML Configuration:
```yaml
mqtt_user: "your_mqtt_username"
mqtt_password: "your_mqtt_password"
devices:
  - name: "Router"
    ip: "192.168.1.1"
  - name: "Living Room TV"
    ip: "192.168.1.50"
  - name: "NAS Storage"
    ip: "192.168.1.100"
```

### Options:
- **mqtt_user**: Your MQTT broker username.
- **mqtt_password**: Your MQTT broker password.
- **devices**: A list of devices to monitor. Each entry needs a name and an ip.

## 📊 Dashboard Visualization
I recommend using the Auto-entities card from HACS to automatically display offline devices:

```YAML

type: custom:auto-entities
card:
  type: entities
  title: "Network Status"
  state_color: true
filter:
  include:
    - entity_id: "binary_sensor.iot_*"
sort:
  method: state
  reverse: true
```

## 🛠️ Requirements
An active MQTT Broker (like Mosquitto Add-on).

Home Assistant MQTT Integration configured.



###Created by Vladimir
