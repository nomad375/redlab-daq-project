import os
import time
from uldaq import (get_daq_device_inventory, DaqDevice, InterfaceType, 
                   TcType, ULException, TempScale)
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# Configuration from environment variables
URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
TOKEN = os.getenv("INFLUX_TOKEN")
ORG = os.getenv("INFLUX_ORG")
BUCKET = os.getenv("INFLUX_BUCKET")

def get_device():
    """Locate and connect to the RedLab-TC device."""
    while True:
        try:
            devices = get_daq_device_inventory(InterfaceType.USB)
            if devices:
                dev = DaqDevice(devices[0])
                dev.connect()
                print(f">>> Connected: {devices[0].product_name}")
                return dev
            print("--- Waiting for RedLab-TC USB device...")
        except Exception as e:
            print(f"!!! Connection error: {e}")
        time.sleep(5)

def main():
    # Initialize InfluxDB Client
    client = InfluxDBClient(url=URL, token=TOKEN, org=ORG)
    write_api = client.write_api(write_options=SYNCHRONOUS)
    
    while True:
        daq_device = None
        try:
            daq_device = get_device()
            ai_device = daq_device.get_ai_device()
            ai_config = ai_device.get_config()
            
            # Init all 8 channels as K-type thermocouples
            for ch in range(8):
                ai_config.set_chan_tc_type(ch, TcType.K)
            
            print(">>> Data acquisition loop started...")
            
            while True:
                points = []
                log_data = []  # <--- Fix: Initialize the list here

                for ch in range(8):
                    try:
                        temp = ai_device.t_in(ch, TempScale.CELSIUS)
                        
                        # Filter: Save only if sensor is connected (Open TC Detection)
                        if -270 < temp < 2000:
                            # Add data point for InfluxDB
                            points.append(
                                Point("temperature")
                                .tag("channel", f"ch{ch}")
                                .field("value", float(temp))
                            )
                            # Add formatted string for console logging
                            log_data.append(f"CH{ch}:{temp:.1f}")
                    except:
                        continue

                # Batch write points to InfluxDB
                if points:
                    try:
                        write_api.write(BUCKET, ORG, points)
                        # Print detailed log only if points were recorded
                        if log_data:
                            print(f"Data logged ({len(points)} channels): " + " | ".join(log_data))
                    except Exception as e:
                        print(f"!!! InfluxDB Write Error: {e}")
                else:
                    print("--- No active thermocouples detected ---")

                time.sleep(1)

        except Exception as e:
            print(f"!!! Runtime error: {e}")
        finally:
            if daq_device and daq_device.is_connected():
                daq_device.disconnect()
            print("Attempting to reconnect in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    main()