from __future__ import print_function
import cantools
import time
import can
import struct
import sys
import threading
from typing import Dict, Any, Optional

# --- Configuration ---
MASTERBUS_INTERFACE = 'can1'
PYLONTECH_INTERFACE = 'can0'
BITRATE = 500000
READ_TIMEOUT = 0.1

# MasterBus Specifics (VERIFIED from log output)
MASTERBUS_DEVICE_ADDR_HEX = "EA" # Verified Device Address

# Mapping MasterBus Parameter IDs to their internal keys (VERIFIED from log output)
MASTERBUS_PARAM_MAP = {
    f"{MASTERBUS_DEVICE_ADDR_HEX}_0000": "SoC",        # Confirmed on 0000 (Value 12.685)
    f"{MASTERBUS_DEVICE_ADDR_HEX}_0001": "Voltage",    # Confirmed on 0001 (Value 52.828)
    f"{MASTERBUS_DEVICE_ADDR_HEX}_0002": "Current",    # Confirmed on 0002 (Value 30.353)
    f"{MASTERBUS_DEVICE_ADDR_HEX}_008B": "Temperature",# Using 008B (Value 26.392, common temp signal)
    # The 'Power' parameter (0003) is removed as it wasn't requested for forwarding.
}

# Global state to share the latest values between threads
shared_state: Dict[str, Any] = {
    "SoC": 50,          # Default SoC (50%)
    "Voltage": 52.0,    # Default Voltage (V)
    "Current": 0.0,     # Default Current (A)
    "Temperature": 25.0,# Default Temperature (C)
    "timestamp": 0.0
}

# Load the Pylontech DBC file
try:
    # Ensure 'pylon_CAN_210124.dbc' is in the same directory
    db = cantools.db.load_file('pylon_CAN_210124.dbc')
except Exception as e:
    print(f"Error loading DBC file: {e}")
    sys.exit(1)

# Pylontech Message Definitions
Network_alive_msg = db.get_message_by_name('Network_alive_msg')
Battery_SoC_SoH = db.get_message_by_name('Battery_SoC_SoH')
Battery_Manufacturer = db.get_message_by_name('Battery_Manufacturer')
Battery_Request = db.get_message_by_name('Battery_Request')
Battery_actual_values_UIt = db.get_message_by_name('Battery_actual_values_UIt')
Battery_limits = db.get_message_by_name('Battery_limits')
Battery_Error_Warnings = db.get_message_by_name('Battery_Error_Warnings')

# --- Static Pylontech Message Data ---
msg_data_Battery_Request = {
    'Full_charge_req': 0, 'Force_charge_req_II': 0, 'Force_charge_req_I': 0, 
    'Discharge_enable': 1, 'Charge_enable': 1
}
msg_data_Battery_Error_Warnings = {
    'Module_numbers': 16, 'Charge_current_high_WARN': 0, 'Internal_Error_WARN': 0, 
    'voltage_low_WARN': 0, 'voltage_high_WARN': 0, 'Temperature_high_WARN': 0, 
    'Temperature_low_WARN': 0, 'Discharge_current_high_WARN': 0, 'Charge_overcurrent_ERR': 0, 
    'System_Error': 0, 'Overvoltage_ERR': 0, 'Undervoltage_ERR': 0, 'Overtemperature_ERR': 0, 
    'Undertemperature_ERR': 0, 'Overcurrent_discharge_ERR': 0
}
msg_data_enc_Battery_Manufacturer = b'\x50\x59\x4c\x4f\x4e\x00\x00\x00' # 'PYLON'

# Initial CAN Message objects (data will be set dynamically or are static)
msg_tx_Network_alive_msg = can.Message(arbitration_id=Network_alive_msg.frame_id, is_extended_id=False)
msg_tx_Battery_SoC_SoH = can.Message(arbitration_id=Battery_SoC_SoH.frame_id, is_extended_id=False)
msg_tx_Battery_Manufacturer = can.Message(arbitration_id=Battery_Manufacturer.frame_id, data=msg_data_enc_Battery_Manufacturer, is_extended_id=False)
msg_tx_Battery_Request = can.Message(arbitration_id=Battery_Request.frame_id, data=db.encode_message('Battery_Request', msg_data_Battery_Request), is_extended_id=False)
msg_tx_Battery_actual_values_UIt = can.Message(arbitration_id=Battery_actual_values_UIt.frame_id, is_extended_id=False)
msg_tx_Battery_limits = can.Message(arbitration_id=Battery_limits.frame_id, is_extended_id=False)
msg_tx_Battery_Error_Warnings = can.Message(arbitration_id=Battery_Error_Warnings.frame_id, data=db.encode_message('Battery_Error_Warnings', msg_data_Battery_Error_Warnings), is_extended_id=False)


def ieee754_decode(data_bytes) -> Optional[float]:
    """Decodes 4 bytes (MasterBus Little-Endian) into a float."""
    if len(data_bytes) != 4:
        return None
    try:
        # '<f' means: Little-endian (<), single-precision float (f)
        return struct.unpack('<f', data_bytes)[0]
    except struct.error:
        return None

def masterbus_receiver(bus: can.Bus):
    """Listens on MasterBus (can1) and updates the shared state."""
    print(f"MasterBus receiver running on {MASTERBUS_INTERFACE}...")
    while True:
        try:
            msg = bus.recv(timeout=READ_TIMEOUT) 
            if msg is not None:
                # Filter for 6-byte data messages with the 0x08 prefix
                if msg.dlc == 6 and (msg.arbitration_id >> 24) == 0x08:
                    device_address = msg.arbitration_id & 0xFF
                    device_address_hex = f"{device_address:02X}"

                    # Ensure we are only processing data from the target device "EA"
                    if device_address_hex != MASTERBUS_DEVICE_ADDR_HEX:
                        continue 

                    # Parameter ID is stored Little-Endian in data[1], data[0]
                    param_id_hex = f"{msg.data[1]:02X}{msg.data[0]:02X}"

                    key = f"{device_address_hex}_{param_id_hex}"

                    if key in MASTERBUS_PARAM_MAP:
                        float_payload = msg.data[2:6]
                        decoded_float = ieee754_decode(float_payload)

                        if decoded_float is not None:
                            internal_key = MASTERBUS_PARAM_MAP[key]

                            if internal_key == "SoC":
                                # SoC is clamped and rounded to an integer (0-100)
                                value = int(max(0, min(100, round(decoded_float))))
                            else:
                                # Other values (Voltage, Current, Temp) are rounded to 2 decimal places
                                value = round(decoded_float, 2) 

                            if shared_state[internal_key] != value:
                                shared_state[internal_key] = value
                                shared_state["timestamp"] = time.time()

        except Exception as e:
            print(f"MasterBus error: {e}")
            time.sleep(1)

def pylontech_sender(bus: can.Bus):
    """Periodically sends Pylontech messages on can0, updating all dynamic values every second."""
    print(f"Pylontech sender running on {PYLONTECH_INTERFACE}...")
    Alive_packet = 0 # CAN alive counter

    # Start all periodic tasks with a 1 second (1) interval
    tasks = {
        'alive': bus.send_periodic(msg_tx_Network_alive_msg, 1),
        'soc': bus.send_periodic(msg_tx_Battery_SoC_SoH, 1),
        'mfr': bus.send_periodic(msg_tx_Battery_Manufacturer, 1),
        'req': bus.send_periodic(msg_tx_Battery_Request, 1),
        'actual': bus.send_periodic(msg_tx_Battery_actual_values_UIt, 1),
        'limits': bus.send_periodic(msg_tx_Battery_limits, 1),
        'errors': bus.send_periodic(msg_tx_Battery_Error_Warnings, 1)
    }

    time.sleep(0.5)

    try:
        while True:
            # 1. Get latest data from shared state
            soc = shared_state["SoC"]
            voltage = shared_state["Voltage"]
            current = shared_state["Current"]
            temp = shared_state["Temperature"]

            # 2. Update Network Alive message (0x350)
            Alive_packet += 1
            msg_tx_Network_alive_msg.data = db.encode_message('Network_alive_msg', {'Alive_packet': Alive_packet})
            tasks['alive'].modify_data(msg_tx_Network_alive_msg)

            # 3. Update Battery SoC/SoH message (0x351)
            msg_tx_Battery_SoC_SoH.data = db.encode_message('Battery_SoC_SoH', {'SoC': soc, 'SoH': 100})
            tasks['soc'].modify_data(msg_tx_Battery_SoC_SoH)

            # 4. Update Battery Actual Values (U, I, t) message (0x356)
            msg_data_Battery_actual_values_UIt = {
                'Battery_temperature': temp,
                'Battery_current': current,
                'Battery_voltage': voltage
            }
            msg_tx_Battery_actual_values_UIt.data = db.encode_message('Battery_actual_values_UIt', msg_data_Battery_actual_values_UIt)
            tasks['actual'].modify_data(msg_tx_Battery_actual_values_UIt)

            # 5. Update Battery Limits message (0x355)
            # IMPORTANT: CUSTOMIZE THIS LIMIT LOGIC FOR YOUR BATTERY'S SAFETY!

            if soc >= 98:
                charge_limit = 5.0
                discharge_limit = -120.0
            elif soc <= 10:
                charge_limit = 120.0
                discharge_limit = -5.0
            else:
                charge_limit = 120.0
                discharge_limit = -120.0

            charge_voltage = 56.0
            discharge_voltage = 48.0

            msg_data_Battery_limits = {
               'Battery_discharge_current_limit' : discharge_limit,
               'Battery_charge_current_limit' : charge_limit,
               'Battery_charge_voltage' : charge_voltage,
               'Battery_discharge_voltage' : discharge_voltage
            }

            msg_tx_Battery_limits.data = db.encode_message('Battery_limits', msg_data_Battery_limits)
            tasks['limits'].modify_data(msg_tx_Battery_limits)

            if Alive_packet >= 4611686018427387904:
                Alive_packet = 2

            # --- LOGGING ---
            print(f"SENT: Time={time.strftime('%H:%M:%S')}, Alive={Alive_packet}, SoC={soc}%, U={voltage:.2f}V, I={current:.2f}A, T={temp:.2f}°C")

            # Wait for the next cycle (1 second interval)
            time.sleep(1)

    except Exception as e:
        print(f"Pylontech sender error: {e}")
    finally:
        # Stop all periodic tasks upon exit
        for task in tasks.values():
            task.stop()
        print("Pylontech periodic sending stopped.")

if __name__ == "__main__":
    master_bus: Optional[can.Bus] = None
    pylon_bus: Optional[can.Bus] = None

    try:
        print("Initializing CAN buses...")

        master_bus = can.interface.Bus(channel=MASTERBUS_INTERFACE, interface='socketcan', bitrate=BITRATE)
        print(f"✅ MasterBus on {MASTERBUS_INTERFACE} ready.")

        pylon_bus = can.interface.Bus(channel=PYLONTECH_INTERFACE, interface='socketcan', bitrate=BITRATE)
        print(f"✅ Pylontech Bus on {PYLONTECH_INTERFACE} ready.")

        # Start the MasterBus receiver in a separate thread 
        receiver_thread = threading.Thread(target=masterbus_receiver, args=(master_bus,), daemon=True)
        receiver_thread.start()

        # Start the Pylontech sender in the main thread (blocking)
        pylontech_sender(pylon_bus)

    except can.exceptions.CanError as e:
        print(f"❌ CAN Bus initialization error: {e}")
        print("Ensure both CAN interfaces are configured and up (e.g., 'sudo ip link set can0 up type can bitrate 500000').")

    except KeyboardInterrupt:
        print("\n\n--- CAN Bridge stopped by user (Ctrl+C) ---")

    finally:
        if master_bus:
            master_bus.shutdown()
        if pylon_bus:
            pylon_bus.shutdown()
        print("Buses closed. Exiting.")
        sys.exit(0)
