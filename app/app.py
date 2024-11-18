import time
from pyzysh import Client
from prometheus_client import start_http_server, Gauge, generate_latest, Counter
from flask import Flask
from datetime import datetime
import yaml, sys
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Get config file path from YAML file from args if provided
if len(sys.argv) > 1:
    _config_path = sys.argv[1]
else:
    _config_path = "config.yaml"

# Load configuration from YAML file
with open(_config_path, "r") as config_file:
    config = yaml.safe_load(config_file)

# Create instance of client with params from config file which have to match each argument of Client class but if not provided, default values will be used
client = Client(**config["target"])

# Login to the device
client.login()

# Instantiate Flask app
app = Flask(__name__)

# Initialize Prometheus counter
request_counter = Counter(
    "http_requests_total", "Total HTTP Requests", ["method", "endpoint"]
)

# Total number of connected devices per SSID and Band
connected_devices_total = Gauge(
    "access_point_connected_devices_total",
    "Total number of devices connected to the access point",
    ["ssid", "band"],
)

# Signal strength in dBm
device_rssi_dbm = Gauge(
    "access_point_device_rssi_dbm",
    "Received Signal Strength Indicator (RSSI) in dBm for each device",
    ["mac", "ipv4", "ssid", "band"],
)

# Transmission rate in Mbps
device_tx_rate_mbps = Gauge(
    "access_point_device_tx_rate_mbps",
    "Transmission rate in Mbps for each device",
    ["mac", "ipv4", "ssid", "band"],
)

# Reception rate in Mbps
device_rx_rate_mbps = Gauge(
    "access_point_device_rx_rate_mbps",
    "Reception rate in Mbps for each device",
    ["mac", "ipv4", "ssid", "band"],
)

# Connection timestamp (converted to Unix timestamp)
device_connection_timestamp_seconds = Gauge(
    "access_point_device_connection_timestamp_seconds",
    "Connection timestamp in seconds since Unix epoch for each device",
    ["mac", "ipv4", "ssid", "band"],
)

# Security protocol type
device_security_type = Gauge(
    "access_point_device_security_type",
    "Security protocol type of each connected device",
    ["mac", "ipv4", "ssid", "band", "security"],
)


# Function to parse the data and update Prometheus metrics
def update_metrics(api_data):
    # If stations is available in the API data
    if "stations" in api_data:
        # Clear all metrics
        connected_devices_total._metrics.clear()
        # Process and update metrics for stations
        for device in api_data["stations"]:
            ssid = device["_SSID"]
            band = device["_Band"]
            mac = device["_MAC"]
            ipv4 = device["_IPv4"]
            tx_rate = float(device["_TxRate"].rstrip("M"))  # Convert "28M" to 28.0
            rx_rate = float(device["_RxRate"].rstrip("M"))  # Convert "54M" to 54.0
            rssi_dbm = int(device["_RSSI_dBm"])
            security = device["_Security"]

            # Parse time to Unix timestamp
            connection_time_str = device["_Time"]
            connection_time = int(
                datetime.strptime(connection_time_str, "%H:%M:%S %Y/%m/%d").timestamp()
            )

            # Update metrics
            connected_devices_total.labels(ssid=ssid, band=band).inc()
            # Increment connected devices
            device_rssi_dbm.labels(mac=mac, ipv4=ipv4, ssid=ssid, band=band).set(
                rssi_dbm
            )
            device_tx_rate_mbps.labels(mac=mac, ipv4=ipv4, ssid=ssid, band=band).set(
                tx_rate
            )
            device_rx_rate_mbps.labels(mac=mac, ipv4=ipv4, ssid=ssid, band=band).set(
                rx_rate
            )
            device_connection_timestamp_seconds.labels(
                mac=mac, ipv4=ipv4, ssid=ssid, band=band
            ).set(connection_time)
            device_security_type.labels(
                mac=mac, ipv4=ipv4, ssid=ssid, band=band, security=security
            ).set(
                1
            )  # Set a constant value


# Function to fetch data from API
def fetch_data_from_api():
    api_data = {}
    try:
        api_data["stations"] = client.exec("show wireless-hal station info")[0][
            "_index"
        ]
    except Exception as e:
        print(f"Failed to fetch stations data from API: {e}")
    return api_data


@app.route("/metrics")
def metrics():
    # Increment the counter for the metrics endpoint
    request_counter.labels("GET", "/metrics").inc()
    # Fetch data from API
    api_data = fetch_data_from_api()
    # Update Prometheus metrics
    update_metrics(api_data)
    # Return the metrics
    return generate_latest()


if __name__ == "__main__":
    # Start the Flask app on port 8080
    app.run(port=8080, host="0.0.0.0")
