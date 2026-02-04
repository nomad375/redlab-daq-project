import os
import sys
import time
import glob
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# Add MSCL to path
sys.path.append('/usr/share/python3-mscl')
try:
    import mscl
except ImportError:
    print("!!! Critical: MSCL not found. Check Dockerfile installation.")
    sys.exit(1)

# InfluxDB Configuration
URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
TOKEN = os.getenv("INFLUX_TOKEN")
ORG = os.getenv("INFLUX_ORG")
BUCKET = os.getenv("INFLUX_BUCKET")

def find_base_station():
    """Scan for MicroStrain Base Station on common USB ports."""
    ports = glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*')
    for port in ports:
        try:
            connection = mscl.Connection.Serial(port)
            base_station = mscl.BaseStation(connection)
            print(f">>> Found BaseStation on {port}")
            return base_station
        except:
            continue
    return None

def main():
    print(f">>> Starting MSCL Collector (Version {mscl.MSCL_VERSION})")
    
    # Initialize InfluxDB
    db_client = InfluxDBClient(url=URL, token=TOKEN, org=ORG)
    write_api = db_client.write_api(write_options=SYNCHRONOUS)

    # Connect to Hardware
    base_station = find_base_station()
    if not base_station:
        print("!!! Error: No BaseStation found. Ensure it is plugged in.")
        sys.exit(1)

    print(">>> Listening for wireless nodes...")
    
    while True:
        try:
            # Check for data packets (timeout 500ms)
            packets = base_station.getData(500)
            
            for packet in packets:
                points = []
                node_address = packet.nodeAddress()
                
                for data_point in packet.data():
                    # Create InfluxDB Point for each channel
                    p = Point("microstrain") \
                        .tag("node", str(node_address)) \
                        .tag("channel", data_point.channelName()) \
                        .field("value", data_point.as_float())
                    points.append(p)
                
                if points:
                    write_api.write(BUCKET, ORG, points)
                    print(f"Node {node_address}: Logged {len(points)} data points.")

        except mscl.Error as e:
            # Handle empty queue or hardware issues
            if "Connection error" in str(e):
                print(f"!!! Connection lost: {e}")
                sys.exit(1)
            time.sleep(0.1)
        except Exception as e:
            print(f"!!! Runtime error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()