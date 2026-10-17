"""Generate seed data: companies, locations and devices.

Usage:
    python -m simulator.seed --seed 42 --output output/seed.json
"""

import argparse
import json
import random
from dataclasses import asdict
from pathlib import Path
from typing import TypedDict
from uuid import UUID

from simulator.models import (
    Company,
    Device,
    DeviceConfiguration,
    DeviceStatus,
    DeviceType,
    Location,
    LocationType,
    SeedData,
    SensorType,
)


class DeviceSpec(TypedDict):
    device_type: DeviceType
    count: int
    status: DeviceStatus
    sampling_interval_seconds: int
    enabled_sensors: tuple[SensorType, ...]


class LocationSpec(TypedDict):
    name: str
    location_type: LocationType
    devices: list[DeviceSpec]


class CompanySpec(TypedDict):
    name: str
    locations: list[LocationSpec]


# Which sensors each kind of device has. Defined once, reused in every spec below.
COLD_STORAGE_SENSORS = (SensorType.TEMPERATURE, SensorType.HUMIDITY, SensorType.BATTERY)
VEHICLE_TRACKER_SENSORS = (SensorType.BATTERY, SensorType.GPS)

# What the simulated world looks like. IDs are not written here: they come from the seed.
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
                        "status": DeviceStatus.ACTIVE,
                        "sampling_interval_seconds": 60,
                        "enabled_sensors": COLD_STORAGE_SENSORS,
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
                        "status": DeviceStatus.ACTIVE,
                        "sampling_interval_seconds": 30,
                        "enabled_sensors": VEHICLE_TRACKER_SENSORS,
                    },
                    {
                        "device_type": DeviceType.COLD_STORAGE_SENSOR,
                        "count": 2,
                        "status": DeviceStatus.ACTIVE,
                        "sampling_interval_seconds": 30,
                        "enabled_sensors": COLD_STORAGE_SENSORS,
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
                        "count": 4,
                        "status": DeviceStatus.ACTIVE,
                        "sampling_interval_seconds": 60,
                        "enabled_sensors": COLD_STORAGE_SENSORS,
                    },
                    # Deliberately inactive: the backend must reject its telemetry (403).
                    {
                        "device_type": DeviceType.COLD_STORAGE_SENSOR,
                        "count": 1,
                        "status": DeviceStatus.INACTIVE,
                        "sampling_interval_seconds": 60,
                        "enabled_sensors": COLD_STORAGE_SENSORS,
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
                        "status": DeviceStatus.ACTIVE,
                        "sampling_interval_seconds": 30,
                        "enabled_sensors": VEHICLE_TRACKER_SENSORS,
                    },
                    {
                        "device_type": DeviceType.COLD_STORAGE_SENSOR,
                        "count": 3,
                        "status": DeviceStatus.ACTIVE,
                        "sampling_interval_seconds": 30,
                        "enabled_sensors": COLD_STORAGE_SENSORS,
                    },
                ],
            },
        ],
    },
]


def generate_uuid(rng: random.Random) -> UUID:
    """A UUID that is random, but the same every run for the same seed."""
    return UUID(int=rng.getrandbits(128), version=4)


def build_location(rng: random.Random, spec: LocationSpec) -> Location:
    devices: list[Device] = []
    for device_spec in spec["devices"]:
        for _ in range(device_spec["count"]):
            number = len(devices) + 1
            devices.append(
                Device(
                    id=generate_uuid(rng),
                    name=f"{device_spec['device_type'].lower()}-{number}",
                    device_type=device_spec["device_type"],
                    status=device_spec["status"],
                    configuration=DeviceConfiguration(
                        sampling_interval_seconds=device_spec["sampling_interval_seconds"],
                        enabled_sensors=device_spec["enabled_sensors"],
                    ),
                )
            )
    return Location(
        id=generate_uuid(rng),
        name=spec["name"],
        location_type=spec["location_type"],
        devices=tuple(devices),
    )


def build_company(rng: random.Random, spec: CompanySpec) -> Company:
    return Company(
        id=generate_uuid(rng),
        name=spec["name"],
        locations=tuple(build_location(rng, location) for location in spec["locations"]),
    )


def generate_seed(seed: int, company_specs: list[CompanySpec]) -> SeedData:
    """Pure function: same seed and specs always give the same result. No file I/O."""
    rng = random.Random(seed)
    return SeedData(
        seed=seed,
        companies=tuple(build_company(rng, spec) for spec in company_specs),
    )


def write_seed(seed_data: SeedData, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # default=str turns UUID values into plain strings. StrEnum values are already strings.
    path.write_text(json.dumps(asdict(seed_data), indent=2, default=str) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate simulator seed data.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("output/seed.json"))
    args = parser.parse_args()

    seed_data = generate_seed(args.seed, COMPANY_SPECS)
    write_seed(seed_data, args.output)

    device_count = sum(
        len(location.devices) for company in seed_data.companies for location in company.locations
    )
    print(f"Wrote {len(seed_data.companies)} companies, {device_count} devices to {args.output}")


if __name__ == "__main__":
    main()
