
import requests
import cantools
import can
import time
import sys

# --- Configuration ---
API_BASE_URL = "http://localhost:8000/api"
CAN_INTERFACE = "can0"
DBC_FILE = "pylon_CAN_210124.dbc"
BATTERY_DEVICE_ID = 7165674  # BAT 1 (Cluster) as per user's device list
CHARGER_DEVICE_ID = 2667145  # As per user's request

# --- Main Application ---

def get_masterbus_value(device_id, field_id):
    """Fetches a single value from the MasterBus API."""
    try:
        # Using a timeout for the request
        response = requests.get(f"{API_BASE_URL}/devices/{device_id}/fields/{field_id}/value", timeout=5)
        response.raise_for_status()
        data = response.json()
        return data.get("value")
    except requests.exceptions.RequestException as e:
        # Don't print endlessly if the API is down, just return None
        return None

def main():
    """
    Main loop to fetch data from MasterBus API and send it to the CAN bus.
    """
    # Load the DBC file
    try:
        db = cantools.database.load_file(DBC_FILE)
    except FileNotFoundError:
        print(f"Error: DBC file not found at '{DBC_FILE}'", file=sys.stderr)
        sys.exit(1)

    # Get message definitions from DBC
    network_alive_msg_def = db.get_message_by_name('Network_alive_msg')
    soc_soh_msg_def = db.get_message_by_name('Battery_SoC_SoH')
    uit_msg_def = db.get_message_by_name('Battery_actual_values_UIt')
    limits_msg_def = db.get_message_by_name('Battery_limits')
    req_msg_def = db.get_message_by_name('Battery_Request')
    err_warn_msg_def = db.get_message_by_name('Battery_Error_Warnings')
    man_msg_def = db.get_message_by_name('Battery_Manufacturer')
    
    # Initialize CAN bus
    bus = None
    try:
        # Corrected 'bustype' to 'interface' to fix deprecation warning
        bus = can.interface.Bus(channel=CAN_INTERFACE, interface='socketcan')
        print(f"Successfully connected to CAN bus '{CAN_INTERFACE}'.")
    except Exception as e:
        print(f"Error initializing CAN bus '{CAN_INTERFACE}': {e}", file=sys.stderr)
        sys.exit(1)

    print("Starting data bridge...")

    # --- Setup Periodic CAN Messages ---
    # All messages must be created with is_extended_id=False for standard CAN IDs.
    
    # Message: Battery_Request (ID 860) - Static
    msg_data_req = req_msg_def.encode({'Charge_enable': 1, 'Discharge_enable': 1, 'Force_charge_req_I': 0, 'Force_charge_req_II': 0, 'Full_charge_req': 0})
    req_msg = can.Message(arbitration_id=req_msg_def.frame_id, data=msg_data_req, is_extended_id=False)
    
    # Message: Battery_Error_Warnings (ID 857) - Static
    msg_data_err = err_warn_msg_def.encode({'Module_numbers': 1, 'Charge_current_high_WARN': 0, 'Internal_Error_WARN': 0, 'voltage_low_WARN': 0, 'voltage_high_WARN': 0, 'Temperature_high_WARN': 0, 'Temperature_low_WARN': 0, 'Discharge_current_high_WARN': 0, 'Charge_overcurrent_ERR': 0, 'System_Error': 0, 'Overvoltage_ERR': 0, 'Undervoltage_ERR': 0, 'Overtemperature_ERR': 0, 'Undertemperature_ERR': 0, 'Overcurrent_discharge_ERR': 0})
    err_warn_msg = can.Message(arbitration_id=err_warn_msg_def.frame_id, data=msg_data_err, is_extended_id=False)

    # Message: Battery_Manufacturer (ID 862) - Static. Data must be 8 bytes.
    man_msg = can.Message(arbitration_id=man_msg_def.frame_id, data=b'PYLON\x00\x00\x00', is_extended_id=False)

    # Messages to be updated in the loop - must also be initialized correctly.
    alive_msg = can.Message(arbitration_id=network_alive_msg_def.frame_id, is_extended_id=False)
    soc_soh_msg = can.Message(arbitration_id=soc_soh_msg_def.frame_id, is_extended_id=False)
    uit_msg = can.Message(arbitration_id=uit_msg_def.frame_id, is_extended_id=False)
    limits_msg = can.Message(arbitration_id=limits_msg_def.frame_id, is_extended_id=False)

    tasks = {
        'alive': bus.send_periodic(alive_msg, 1.0),
        'soc': bus.send_periodic(soc_soh_msg, 1.0),
        'uit': bus.send_periodic(uit_msg, 1.0),
        'limits': bus.send_periodic(limits_msg, 1.0),
        'req': bus.send_periodic(req_msg, 1.0),
        'err': bus.send_periodic(err_warn_msg, 1.0),
        'man': bus.send_periodic(man_msg, 1.0),
    }

    alive_counter = 0
    last_api_success_time = time.time()

    try:
        while True:
            # 1. Fetch data from MasterBus API
            # Battery Data
            soc = get_masterbus_value(BATTERY_DEVICE_ID, 0) # State of charge (%)
            voltage = get_masterbus_value(BATTERY_DEVICE_ID, 1) # Battery (V)
            battery_current = get_masterbus_value(BATTERY_DEVICE_ID, 2) # Battery (A)
            temperature = get_masterbus_value(BATTERY_DEVICE_ID, 5) # Battery (°C)
            
            # Charger Data
            charger_current = get_masterbus_value(CHARGER_DEVICE_ID, 15) # Battery current (A)

            if any(v is None for v in [soc, voltage, battery_current, temperature]):
                if time.time() - last_api_success_time > 5:
                     print("API fetch failed for primary battery data. Check masterbus-fastapi service.", file=sys.stderr)
                time.sleep(1)
                continue
            
            last_api_success_time = time.time()

            # 2. Process and sanitize data
            soc = int(max(0, min(100, round(soc))))
            voltage = round(voltage, 2)
            battery_current = round(battery_current, 2)
            temperature = round(temperature, 2)
            
            # Adjust current based on charger state
            adjusted_current = battery_current
            log_charger_current = 0.0
            if charger_current is not None and charger_current > 1.0:
                charger_current = round(charger_current, 2)
                adjusted_current -= charger_current
                log_charger_current = charger_current

            # 3. Update CAN message data
            
            # Alive message
            alive_counter = (alive_counter + 1) % 256
            alive_msg.data = network_alive_msg_def.encode({'Alive_packet': alive_counter})
            tasks['alive'].modify_data(alive_msg)
            
            # SoC/SoH message
            soc_soh_msg.data = soc_soh_msg_def.encode({'SoC': soc, 'SoH': 100}) # Assume SoH 100%
            tasks['soc'].modify_data(soc_soh_msg)

            # Actual values message - USE ADJUSTED CURRENT
            uit_msg.data = uit_msg_def.encode({
                'Battery_voltage': voltage, 
                'Battery_current': adjusted_current, 
                'Battery_temperature': temperature
            })
            tasks['uit'].modify_data(uit_msg)
            
            # Dynamic battery limits
            if soc >= 98:
                charge_limit = 20.0
                discharge_limit = -100.0
            elif soc <= 15:
                charge_limit = 100.0
                discharge_limit = -20.0
            else:
                charge_limit = 100.0
                discharge_limit = -100.0

            limits_msg.data = limits_msg_def.encode({
               'Battery_discharge_current_limit' : discharge_limit,
               'Battery_charge_current_limit' : charge_limit,
               'Battery_charge_voltage' : 54.5,
               'Battery_discharge_voltage' : 48.0
            })
            tasks['limits'].modify_data(limits_msg)

            print(f"SENT: Time={time.strftime('%H:%M:%S')}, SoC={soc}%, U={voltage:.2f}V, I={adjusted_current:.2f}A (Bat: {battery_current:.2f}A, Chg: {log_charger_current:.2f}A), T={temperature:.2f}°C")

            time.sleep(1)

    except KeyboardInterrupt:
        print("\nShutting down bridge...")
    except Exception as e:
        print(f"An unhandled error occurred: {e}", file=sys.stderr)
    finally:
        # Stop all periodic tasks
        for task in tasks.values():
            if task:
                task.stop()
        if bus:
            bus.shutdown()
        print("CAN bridge stopped.")


if __name__ == "__main__":
    # Wait a few seconds for the API to be ready
    print("Bridge starting in 5 seconds...")
    time.sleep(5)
    main()
