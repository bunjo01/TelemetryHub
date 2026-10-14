"""Seed data models: what exists in the simulated world.

Owned by the simulator. Never imported from or by the backend.
"""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class SensorType(StrEnum):
    TEMPERATURE = "TEMPERATURE"
    HUMIDITY = "HUMIDITY"
    BATTERY = "BATTERY"
    GPS = "GPS"


class DeviceStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    MAINTENANCE = "MAINTENANCE"


class DeviceType(StrEnum):
    COLD_STORAGE_SENSOR = "COLD_STORAGE_SENSOR"
    VEHICLE_TRACKER = "VEHICLE_TRACKER"


class LocationType(StrEnum):
    WAREHOUSE = "WAREHOUSE"
    VEHICLE = "VEHICLE"
    COLD_ROOM = "COLD_ROOM"
    LABORATORY = "LABORATORY"
    OTHER = "OTHER"


@dataclass(frozen=True)
class DeviceConfiguration:
    sampling_interval_seconds: int
    enabled_sensors: tuple[SensorType, ...]
    firmware_version: str | None = None

@dataclass(frozen=True)
class Device:
    id: UUID
    name: str
    device_type: DeviceType
    status: DeviceStatus
    configuration: DeviceConfiguration


@dataclass(frozen=True)
class Location:
    id: UUID
    name: str
    location_type: LocationType
    devices: tuple[Device, ...]

@dataclass(frozen=True)
class Company:
    id: UUID
    name: str
    locations: tuple[Location, ...]

@dataclass(frozen=True)
class SeedData:
    seed: int
    companies: tuple[Company, ...]