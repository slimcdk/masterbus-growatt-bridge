from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from ctypes import *
from contextlib import asynccontextmanager

# --- Type Definitions and Structures ---

# Load the shared library
try:
    libmasterbus = CDLL("/usr/local/lib/libmasterbus.so")
except OSError as e:
    print("Fatal: Could not load libmasterbus.so from /usr/local/lib or current directory.")
    raise e

class MasterBusAPIContext(Structure): pass
class MasterBusValue(Structure): pass

class MasterBusDate(Structure):
    _fields_ = [("day", c_int), ("mon", c_int), ("year", c_int)]

class MasterBusTime(Structure):
    _fields_ = [("sec", c_int), ("min", c_int), ("hour", c_int), ("days", c_uint32)]

MasterBusDeviceID = c_uint32
MasterBusFieldID = c_int32
MasterBusGroupID = c_int32
ValueType = c_int

# --- Function Prototypes (argtypes and restype) ---

def setup_prototypes():
    # Helper to avoid cluttering the global namespace
    
    # Connection
    libmasterbus.masterbus_api_socketcan.argtypes = [c_char_p]
    libmasterbus.masterbus_api_socketcan.restype = POINTER(MasterBusAPIContext)
    
    # Memory Management
    libmasterbus.masterbus_free.argtypes = [POINTER(MasterBusAPIContext)]
    libmasterbus.masterbus_free.restype = None
    libmasterbus.masterbus_free_device_list.argtypes = [POINTER(MasterBusDeviceID), c_int]
    libmasterbus.masterbus_free_field_list.argtypes = [POINTER(MasterBusFieldID), c_int]
    libmasterbus.masterbus_free_str.argtypes = [c_char_p]
    libmasterbus.masterbus_free_value.argtypes = [POINTER(MasterBusValue)]

    # Device Info
    libmasterbus.masterbus_devices.argtypes = [POINTER(MasterBusAPIContext), POINTER(POINTER(MasterBusDeviceID))]
    libmasterbus.masterbus_devices.restype = c_int
    libmasterbus.masterbus_device_name.argtypes = [POINTER(MasterBusAPIContext), MasterBusDeviceID, POINTER(c_char_p)]
    libmasterbus.masterbus_device_name.restype = c_int
    libmasterbus.masterbus_device_article_number.argtypes = [POINTER(MasterBusAPIContext), MasterBusDeviceID, POINTER(c_char_p)]
    libmasterbus.masterbus_device_article_number.restype = c_int
    libmasterbus.masterbus_device_serial_number.argtypes = [POINTER(MasterBusAPIContext), MasterBusDeviceID, POINTER(c_char_p)]
    libmasterbus.masterbus_device_serial_number.restype = c_int
    libmasterbus.masterbus_device_firmware_version.argtypes = [POINTER(MasterBusAPIContext), MasterBusDeviceID, POINTER(c_char_p)]
    libmasterbus.masterbus_device_firmware_version.restype = c_int
    libmasterbus.masterbus_device_extended_firmware_version.argtypes = [POINTER(MasterBusAPIContext), MasterBusDeviceID, POINTER(c_char_p)]
    libmasterbus.masterbus_device_extended_firmware_version.restype = c_int
    libmasterbus.masterbus_device_status.argtypes = [POINTER(MasterBusAPIContext), MasterBusDeviceID]
    libmasterbus.masterbus_device_status.restype = c_int

    # Monitoring Groups & Fields
    libmasterbus.masterbus_device_nr_of_monitoring_groups.argtypes = [POINTER(MasterBusAPIContext), MasterBusDeviceID]
    libmasterbus.masterbus_device_nr_of_monitoring_groups.restype = c_int
    libmasterbus.masterbus_monitoring_group_name.argtypes = [POINTER(MasterBusAPIContext), MasterBusDeviceID, MasterBusGroupID, POINTER(c_char_p)]
    libmasterbus.masterbus_monitoring_group_name.restype = c_int
    libmasterbus.masterbus_monitoring_group_fields.argtypes = [POINTER(MasterBusAPIContext), MasterBusDeviceID, MasterBusGroupID, POINTER(POINTER(MasterBusFieldID))]
    libmasterbus.masterbus_monitoring_group_fields.restype = c_int
    libmasterbus.masterbus_monitoring_field_name.argtypes = [POINTER(MasterBusAPIContext), MasterBusDeviceID, MasterBusFieldID, POINTER(c_char_p)]
    libmasterbus.masterbus_monitoring_field_name.restype = c_int
    libmasterbus.masterbus_monitoring_field_unit.argtypes = [POINTER(MasterBusAPIContext), MasterBusDeviceID, MasterBusFieldID, POINTER(c_char_p)]
    libmasterbus.masterbus_monitoring_field_unit.restype = c_int
    
    # Value Reading
    libmasterbus.masterbus_monitoring_field_value.argtypes = [POINTER(MasterBusAPIContext), MasterBusDeviceID, MasterBusFieldID]
    libmasterbus.masterbus_monitoring_field_value.restype = POINTER(MasterBusValue)
    libmasterbus.masterbus_value_type.argtypes = [POINTER(MasterBusValue)]
    libmasterbus.masterbus_value_type.restype = ValueType
    libmasterbus.masterbus_value_get_float.argtypes = [POINTER(MasterBusValue)]
    libmasterbus.masterbus_value_get_float.restype = c_float
    libmasterbus.masterbus_value_get_boolean.argtypes = [POINTER(MasterBusValue)]
    libmasterbus.masterbus_value_get_boolean.restype = c_bool
    libmasterbus.masterbus_value_get_date.argtypes = [POINTER(MasterBusValue)]
    libmasterbus.masterbus_value_get_date.restype = MasterBusDate
    libmasterbus.masterbus_value_get_time.argtypes = [POINTER(MasterBusValue)]
    libmasterbus.masterbus_value_get_time.restype = MasterBusTime
    libmasterbus.masterbus_value_get_string.argtypes = [POINTER(MasterBusValue), POINTER(c_char_p)]
    libmasterbus.masterbus_value_get_string.restype = c_int
    libmasterbus.masterbus_value_get_list_index.argtypes = [POINTER(MasterBusValue)]
    libmasterbus.masterbus_value_get_list_index.restype = c_int
    libmasterbus.masterbus_value_get_list_size.argtypes = [POINTER(MasterBusValue)]
    libmasterbus.masterbus_value_get_list_size.restype = c_int
    libmasterbus.masterbus_value_get_list_string.argtypes = [POINTER(MasterBusValue), c_int, POINTER(c_char_p)]
    libmasterbus.masterbus_value_get_list_string.restype = c_int
    libmasterbus.masterbus_value_get_list_device_id.argtypes = [POINTER(MasterBusValue), c_int]
    libmasterbus.masterbus_value_get_list_device_id.restype = MasterBusDeviceID

    # Value Writing
    libmasterbus.masterbus_set_boolean.argtypes = [POINTER(MasterBusAPIContext), MasterBusDeviceID, MasterBusFieldID, c_bool]
    libmasterbus.masterbus_set_boolean.restype = POINTER(MasterBusValue)

setup_prototypes()

# --- FastAPI Application ---

# Global context for the MasterBus API
ctx = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global ctx
    port = "can1"
    encoded_port = port.encode('utf-8')
    ctx = libmasterbus.masterbus_api_socketcan(encoded_port)
    if not ctx:
        raise RuntimeError(f"Failed to connect to SocketCAN port '{port}' on startup.")
    
    print(f"Successfully connected to MasterBus on {port}")
    yield
    
    if ctx:
        libmasterbus.masterbus_free(ctx)
        print("Successfully disconnected from MasterBus")

app = FastAPI(lifespan=lifespan)

class SetBooleanRequest(BaseModel):
    value: bool

def get_ctx():
    if not ctx:
        raise HTTPException(status_code=503, detail="MasterBus context not available. Connection may have failed on startup.")
    return ctx

def process_value(value_ptr: POINTER(MasterBusValue), device_id: int, field_id: int):
    """Helper function to convert a MasterBusValue pointer to a JSON response."""
    if not value_ptr:
        raise HTTPException(status_code=500, detail="Failed to get or set value from MasterBus.")
    
    try:
        v_type = libmasterbus.masterbus_value_type(value_ptr)
        response = {"device_id": device_id, "field_id": field_id, "value_type": v_type}
        
        # VALUE_TYPE_FLOAT = 0
        if v_type == 0: response["value"] = libmasterbus.masterbus_value_get_float(value_ptr)
        # VALUE_TYPE_DATE = 1
        elif v_type == 1: 
            date_val = libmasterbus.masterbus_value_get_date(value_ptr)
            response["value"] = f"{date_val.year:04d}-{date_val.mon:02d}-{date_val.day:02d}"
        # VALUE_TYPE_TIME = 2
        elif v_type == 2:
            time_val = libmasterbus.masterbus_value_get_time(value_ptr)
            response["value"] = f"{time_val.days}d {time_val.hour:02d}:{time_val.min:02d}:{time_val.sec:02d}"
        # VALUE_TYPE_BOOLEAN = 3
        elif v_type == 3: response["value"] = libmasterbus.masterbus_value_get_boolean(value_ptr)
        # VALUE_TYPE_LIST_OPTION = 4, VALUE_TYPE_DEVICE_ID = 6, VALUE_TYPE_EVENTABLE = 7
        elif v_type in [4, 6, 7]:
            index = libmasterbus.masterbus_value_get_list_index(value_ptr)
            size = libmasterbus.masterbus_value_get_list_size(value_ptr)
            options = []
            for i in range(size):
                str_ptr = c_char_p()
                if v_type == 6: # Device ID list
                    dev_id = libmasterbus.masterbus_value_get_list_device_id(value_ptr, i)
                    options.append({"index": i, "device_id": dev_id})
                else: # List Option or Eventable
                    libmasterbus.masterbus_value_get_list_string(value_ptr, i, byref(str_ptr))
                    options.append({"index": i, "text": str_ptr.value.decode('utf-8', 'ignore') if str_ptr.value else None})
                    libmasterbus.masterbus_free_str(str_ptr)
            response["value"] = {"selectedIndex": index, "options": options}
        # VALUE_TYPE_TEXT = 5
        elif v_type == 5:
            str_ptr = c_char_p()
            libmasterbus.masterbus_value_get_string(value_ptr, byref(str_ptr))
            response["value"] = str_ptr.value.decode('utf-8', 'ignore') if str_ptr.value else None
            libmasterbus.masterbus_free_str(str_ptr)
        else:
            response["value"] = "Unsupported or invalid value type"
    finally:
        libmasterbus.masterbus_free_value(value_ptr)
        
    return response

# --- API Endpoints ---

@app.get("/api/devices", summary="Get all device IDs")
def get_devices():
    devices_ptr = POINTER(MasterBusDeviceID)()
    count = libmasterbus.masterbus_devices(get_ctx(), byref(devices_ptr))
    if count < 0: raise HTTPException(status_code=500, detail=f"Failed to get devices (err: {count})")
    try:
        return [devices_ptr[i] for i in range(count)]
    finally:
        libmasterbus.masterbus_free_device_list(devices_ptr, count)

def get_string_from_library(func, device_id: int, a_name: str):
    """Helper for funcs that return a string."""
    str_ptr = c_char_p()
    result = func(get_ctx(), device_id, byref(str_ptr))
    if result < 0: raise HTTPException(status_code=500, detail=f"Failed to get {a_name} (err: {result})")
    try:
        return str_ptr.value.decode('utf-8', 'ignore') if str_ptr.value else None
    finally:
        libmasterbus.masterbus_free_str(str_ptr)

@app.get("/api/devices/{device_id}/name", summary="Get device name")
def get_device_name(device_id: int):
    return {"name": get_string_from_library(libmasterbus.masterbus_device_name, device_id, "name")}

@app.get("/api/devices/{device_id}/article_number", summary="Get device article number")
def get_device_article_number(device_id: int):
    return {"article_number": get_string_from_library(libmasterbus.masterbus_device_article_number, device_id, "article number")}

@app.get("/api/devices/{device_id}/serial_number", summary="Get device serial number")
def get_device_serial_number(device_id: int):
    return {"serial_number": get_string_from_library(libmasterbus.masterbus_device_serial_number, device_id, "serial number")}

@app.get("/api/devices/{device_id}/firmware_version", summary="Get device firmware version")
def get_device_firmware_version(device_id: int):
    return {"firmware_version": get_string_from_library(libmasterbus.masterbus_device_firmware_version, device_id, "firmware version")}

@app.get("/api/devices/{device_id}/extended_firmware_version", summary="Get device extended firmware version")
def get_device_extended_firmware_version(device_id: int):
    return {"extended_firmware_version": get_string_from_library(libmasterbus.masterbus_device_extended_firmware_version, device_id, "extended firmware version")}

@app.get("/api/devices/{device_id}/status", summary="Get device status")
def get_device_status(device_id: int):
    status = libmasterbus.masterbus_device_status(get_ctx(), device_id)
    if status < 0: raise HTTPException(status_code=500, detail=f"Failed to get status (err: {status})")
    return {"status_code": status}

@app.get("/api/devices/{device_id}/monitoring_groups", summary="Get all monitoring groups for a device")
def get_monitoring_groups(device_id: int):
    count = libmasterbus.masterbus_device_nr_of_monitoring_groups(get_ctx(), device_id)
    if count < 0: raise HTTPException(status_code=500, detail=f"Failed to get group count (err: {count})")
    groups = []
    for i in range(count):
        str_ptr = c_char_p()
        libmasterbus.masterbus_monitoring_group_name(get_ctx(), device_id, i, byref(str_ptr))
        groups.append({"group_id": i, "name": str_ptr.value.decode('utf-8', 'ignore') if str_ptr.value else f"Group {i}"})
        libmasterbus.masterbus_free_str(str_ptr)
    return groups

@app.get("/api/devices/{device_id}/monitoring_groups/{group_id}/fields", summary="Get all fields in a monitoring group")
def get_monitoring_group_fields(device_id: int, group_id: int):
    fields_ptr = POINTER(MasterBusFieldID)()
    count = libmasterbus.masterbus_monitoring_group_fields(get_ctx(), device_id, group_id, byref(fields_ptr))
    if count < 0: raise HTTPException(status_code=500, detail=f"Failed to get fields (err: {count})")
    try:
        return [fields_ptr[i] for i in range(count)]
    finally:
        libmasterbus.masterbus_free_field_list(fields_ptr, count)

@app.get("/api/devices/{device_id}/fields/{field_id}/name", summary="Get field name")
def get_monitoring_field_name(device_id: int, field_id: int):
    str_ptr = c_char_p()
    result = libmasterbus.masterbus_monitoring_field_name(get_ctx(), device_id, field_id, byref(str_ptr))
    if result < 0: raise HTTPException(status_code=500, detail=f"Failed to get field name (err: {result})")
    try:
        return {"name": str_ptr.value.decode('utf-8', 'ignore') if str_ptr.value else None}
    finally:
        libmasterbus.masterbus_free_str(str_ptr)

@app.get("/api/devices/{device_id}/fields/{field_id}/unit", summary="Get field unit")
def get_monitoring_field_unit(device_id: int, field_id: int):
    str_ptr = c_char_p()
    result = libmasterbus.masterbus_monitoring_field_unit(get_ctx(), device_id, field_id, byref(str_ptr))
    if result < 0: raise HTTPException(status_code=500, detail=f"Failed to get field unit (err: {result})")
    try:
        return {"unit": str_ptr.value.decode('utf-8', 'ignore') if str_ptr.value else None}
    finally:
        libmasterbus.masterbus_free_str(str_ptr)

@app.get("/api/devices/{device_id}/fields/{field_id}/value", summary="Get field value")
def get_monitoring_field_value(device_id: int, field_id: int):
    value_ptr = libmasterbus.masterbus_monitoring_field_value(get_ctx(), device_id, field_id)
    return process_value(value_ptr, device_id, field_id)

@app.post("/api/devices/{device_id}/fields/{field_id}/set_boolean", summary="Set a boolean value")
def set_boolean_value(device_id: int, field_id: int, req_body: SetBooleanRequest):
    """
    Sets the value for a boolean field that holds a state (on/off).
    For triggering event-based actions like relays, use the /trigger endpoint.
    The library returns the new state of the value after setting it.
    """
    value_ptr = libmasterbus.masterbus_set_boolean(get_ctx(), device_id, field_id, req_body.value)
    return process_value(value_ptr, device_id, field_id)

@app.post("/api/devices/{device_id}/fields/{field_id}/trigger", summary="Trigger an event field")
def trigger_event(device_id: int, field_id: int):
    """
    Triggers an event-based field, such as 'Open relay' or 'Close relay'.
    This action does not require a request body. The library is called with a 'true' value
    to initiate the event. The returned value represents the new state.
    """
    value_ptr = libmasterbus.masterbus_set_boolean(get_ctx(), device_id, field_id, True)
    return process_value(value_ptr, device_id, field_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)