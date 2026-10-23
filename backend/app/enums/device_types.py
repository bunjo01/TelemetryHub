from enum import StrEnum


class DeviceType(StrEnum):
    TEMPERATURE_SENSOR = "temperature_sensor"
    ENVIRONMENT_SENSOR = "environment_sensor"
    GPS_TRACKER = "gps_tracker"
