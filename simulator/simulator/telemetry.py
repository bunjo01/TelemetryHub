import argparse
import json
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from simulator.models import Device, DeviceType, SeedData, SensorType, TelemetryEvent
from simulator.seed import generate_uuid, load_seed


def drift_toward(
    rng: random.Random,
    current: float,
    target: float,
    pull: float,
    noise_std: float,
) -> float:
    return current + pull * (target - current) + rng.gauss(0, noise_std)


def device_rng(seed: int, device: Device, start: datetime) -> random.Random:
    """Independent, reproducible randomness for one device in one run."""
    return random.Random(f"{seed}:{device.id}:{start.isoformat()}")


@dataclass(frozen=True)
class DeviceProfile:
    temperature_target_c: float
    humidity_target_pct: float
    battery_drain_pct_per_hour: float
    start_latitude: float
    start_longitude: float


PROFILES: dict[DeviceType, DeviceProfile] = {
    DeviceType.COLD_STORAGE_SENSOR: DeviceProfile(
        temperature_target_c=4.0,
        humidity_target_pct=60.0,
        battery_drain_pct_per_hour=0.05,
        start_latitude=45.2671,
        start_longitude=19.8335,
    ),
    DeviceType.VEHICLE_TRACKER: DeviceProfile(
        temperature_target_c=5.0,
        humidity_target_pct=55.0,
        battery_drain_pct_per_hour=0.5,
        start_latitude=45.2671,
        start_longitude=19.8335,
    ),
}


def generate_device_events(
    rng: random.Random,
    device: Device,
    start: datetime,
    duration: timedelta,
) -> list[TelemetryEvent]:
    profile = PROFILES[device.device_type]
    sensors = device.configuration.enabled_sensors
    interval = timedelta(seconds=device.configuration.sampling_interval_seconds)

    temperature = profile.temperature_target_c
    humidity = profile.humidity_target_pct
    battery = 100.0
    latitude = profile.start_latitude
    longitude = profile.start_longitude

    events: list[TelemetryEvent] = []
    event_time = start

    while event_time < start + duration:
        temperature = drift_toward(
            rng, temperature, profile.temperature_target_c, pull=0.1, noise_std=0.15
        )

        humidity = drift_toward(
            rng, humidity, profile.humidity_target_pct, pull=0.05, noise_std=0.5
        )

        battery_drain = profile.battery_drain_pct_per_hour * interval.total_seconds() / 3600

        battery = max(0.0, battery - battery_drain)

        latitude += rng.gauss(0, 0.0005)
        longitude += rng.gauss(0, 0.0005)

        event = TelemetryEvent(
            schema_version=1,
            event_id=generate_uuid(rng),
            device_id=device.id,
            event_time=event_time,
            temperature_c=round(temperature, 2) if SensorType.TEMPERATURE in sensors else None,
            humidity_pct=round(humidity, 2) if SensorType.HUMIDITY in sensors else None,
            battery_pct=round(battery, 2) if SensorType.BATTERY in sensors else None,
            latitude=round(latitude, 6) if SensorType.GPS in sensors else None,
            longitude=round(longitude, 6) if SensorType.GPS in sensors else None,
        )

        events.append(event)
        event_time += interval

    return events


def event_to_json_dict(event: TelemetryEvent) -> dict[str, Any]:
    """Convert a telemetry event to the JSON contract format."""
    return {
        "schema_version": event.schema_version,
        "event_id": str(event.event_id),
        "device_id": str(event.device_id),
        "event_time": event.event_time.isoformat().replace("+00:00", "Z"),
        "temperature_c": event.temperature_c,
        "humidity_pct": event.humidity_pct,
        "battery_pct": event.battery_pct,
        "latitude": event.latitude,
        "longitude": event.longitude,
    }


def all_devices(seed_data: SeedData) -> list[Device]:
    return [
        device
        for company in seed_data.companies
        for location in company.locations
        for device in location.devices
    ]


def generate_all_events(
    seed_data: SeedData,
    start: datetime,
    duration: timedelta,
) -> list[TelemetryEvent]:
    events: list[TelemetryEvent] = []

    for device in all_devices(seed_data):
        rng = device_rng(seed_data.seed, device, start)

        events.extend(generate_device_events(rng, device, start, duration))

    events.sort(key=lambda event: (event.event_time, str(event.device_id)))

    return events


def write_events(events: list[TelemetryEvent], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        for event in events:
            line = json.dumps(event_to_json_dict(event))
            file.write(line + "\n")


def parse_start(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)

    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError("start must be UTC, e.g. 2026-10-01T00:00:00Z")

    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate device telemetry from seed data.")

    parser.add_argument(
        "--seed-file",
        type=Path,
        default=Path("output/seed.json"),
    )
    parser.add_argument("--start", type=parse_start, required=True)
    parser.add_argument("--duration-minutes", type=int, default=60)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/telemetry.jsonl"),
    )

    args = parser.parse_args()

    seed_data = load_seed(args.seed_file)

    events = generate_all_events(
        seed_data,
        args.start,
        timedelta(minutes=args.duration_minutes),
    )

    write_events(events, args.output)


if __name__ == "__main__":
    main()
