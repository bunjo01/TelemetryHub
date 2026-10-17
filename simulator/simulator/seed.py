import argparse
import json
import random
from dataclasses import asdict
from pathlib import Path
from typing import TypedDict
from uuid import UUID

from simulator.models import Company, Device, DeviceType, Location, LocationType, SeedData

class DeviceSpec(TypedDict):
    device_type: DeviceType
    count: int
    sampling_interval_seconds: int


class LocationSpec(TypedDict):
    name: str
    location_type: LocationType
    devices: list[DeviceSpec]


class CompanySpec(TypedDict):
    name: str
    locations: list[LocationSpec]


COMPANY_SPECS: list[CompanySpec] = [
    {
        "name": "ColdChain Pharma",
        "locations": [
            {
                "name": "Novi Sad Warehouse",
                "location_type": LocationType.WAREHOUSE,
                "devices": [
                    {
                        "device_type": DeviceType.COLD_STORAGE_SENSOR,
                        "count": 3,
                        "sampling_interval_seconds": 60,
                    },
                ],
            },
            {
                "name": "Truck NS-123-AB",
                "location_type": LocationType.VEHICLE,
                "devices": [
                    {
                        "device_type": DeviceType.VEHICLE_TRACKER,
                        "count": 1,
                        "sampling_interval_seconds": 30,
                    },
                    {
                        "device_type": DeviceType.COLD_STORAGE_SENSOR,
                        "count": 2,
                        "sampling_interval_seconds": 30,
                    },
                ],
            },
        ],
    },
    {
        "name": "FreshLogistics",
        "locations": [
            {
                "name": "Fresh Food Warehouse",
                "location_type": LocationType.WAREHOUSE,
                "devices": [
                    {
                        "device_type": DeviceType.COLD_STORAGE_SENSOR,
                        "count": 5,
                        "sampling_interval_seconds": 60,
                    },
                ],
            },
            {
                "name": "Truck NS-456-CD",
                "location_type": LocationType.VEHICLE,
                "devices": [
                    {
                        "device_type": DeviceType.VEHICLE_TRACKER,
                        "count": 1,
                        "sampling_interval_seconds": 30,
                    },
                    {
                        "device_type": DeviceType.COLD_STORAGE_SENSOR,
                        "count": 3,
                        "sampling_interval_seconds": 30,
                    },
                ],
            },
        ],
    },
]
