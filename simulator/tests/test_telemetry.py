import random
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from simulator.models import (
    Device,
    DeviceConfiguration,
    DeviceStatus,
    DeviceType,
    SensorType,
)
from simulator.seed import COMPANY_SPECS, generate_seed
from simulator.telemetry import (
    device_rng,
    drift_toward,
    event_to_json_dict,
    generate_all_events,
    generate_device_events,
    parse_start,
)


def test_without_noise_moves_toward_target() -> None:
    rng = random.Random(1)
    assert drift_toward(rng, current=6.0, target=4.0, pull=0.1, noise_std=0.0) == pytest.approx(5.8)


def test_same_seed_gives_same_values() -> None:
    a = drift_toward(random.Random(7), 6.0, 4.0, 0.1, 0.5)
    b = drift_toward(random.Random(7), 6.0, 4.0, 0.1, 0.5)
    assert a == b


def test_stays_near_target_over_many_steps() -> None:
    rng = random.Random(42)
    value = 10.0
    for _ in range(1000):
        value = drift_toward(rng, value, target=4.0, pull=0.1, noise_std=0.2)
    assert 2.0 < value < 6.0


START = datetime(2026, 10, 1, 0, 0, tzinfo=UTC)


def make_device(
    device_type: DeviceType,
    sensors: tuple[SensorType, ...],
) -> Device:
    return Device(
        id=UUID(int=1),
        name="test-device",
        device_type=device_type,
        status=DeviceStatus.ACTIVE,
        configuration=DeviceConfiguration(
            sampling_interval_seconds=60,
            enabled_sensors=sensors,
        ),
    )


def test_one_hour_at_60s_gives_60_events() -> None:
    device = make_device(
        DeviceType.COLD_STORAGE_SENSOR,
        (SensorType.TEMPERATURE,),
    )
    events = generate_device_events(random.Random(1), device, START, timedelta(hours=1))

    assert len(events) == 60
    assert events[0].event_time == START
    assert events[-1].event_time == START + timedelta(minutes=59)


def test_device_without_gps_has_no_coordinates() -> None:
    device = make_device(
        DeviceType.COLD_STORAGE_SENSOR,
        (SensorType.TEMPERATURE, SensorType.HUMIDITY),
    )

    events = generate_device_events(
        random.Random(42),
        device,
        START,
        timedelta(minutes=5),
    )

    for event in events:
        assert event.latitude is None
        assert event.longitude is None


def test_battery_never_increases() -> None:
    device = make_device(
        DeviceType.COLD_STORAGE_SENSOR,
        (SensorType.BATTERY,),
    )

    events = generate_device_events(
        random.Random(42),
        device,
        START,
        timedelta(hours=1),
    )

    batteries = [event.battery_pct for event in events]
    assert None not in batteries

    for previous, current in zip(batteries, batteries[1:], strict=False):
        assert current is not None
        assert previous is not None
        assert current <= previous

    assert events[-1].battery_pct < events[0].battery_pct


def test_event_ids_are_unique() -> None:
    device = make_device(
        DeviceType.COLD_STORAGE_SENSOR,
        (SensorType.TEMPERATURE,),
    )

    events = generate_device_events(
        random.Random(42),
        device,
        START,
        timedelta(hours=1),
    )

    event_ids = [event.event_id for event in events]

    assert len(event_ids) == len(set(event_ids))


def test_different_start_dates_give_different_event_ids() -> None:
    device = make_device(
        DeviceType.COLD_STORAGE_SENSOR,
        (SensorType.TEMPERATURE,),
    )

    next_day = START + timedelta(days=1)

    events_a = generate_device_events(
        device_rng(42, device, START),
        device,
        START,
        timedelta(minutes=5),
    )

    events_b = generate_device_events(
        device_rng(42, device, next_day),
        device,
        next_day,
        timedelta(minutes=5),
    )

    ids_a = {event.event_id for event in events_a}
    ids_b = {event.event_id for event in events_b}

    assert ids_a.isdisjoint(ids_b)


def test_same_inputs_give_same_events() -> None:
    device = make_device(
        DeviceType.COLD_STORAGE_SENSOR,
        (SensorType.TEMPERATURE,),
    )

    events_a = generate_device_events(
        device_rng(42, device, START),
        device,
        START,
        timedelta(minutes=5),
    )

    events_b = generate_device_events(
        device_rng(42, device, START),
        device,
        START,
        timedelta(minutes=5),
    )

    assert events_a == events_b


def test_event_to_json_uses_z_for_utc() -> None:
    device = make_device(
        DeviceType.COLD_STORAGE_SENSOR,
        (SensorType.TEMPERATURE,),
    )

    events = generate_device_events(
        device_rng(42, device, START),
        device,
        START,
        timedelta(minutes=5),
    )

    event_json = event_to_json_dict(events[0])

    assert event_json["event_time"] == "2026-10-01T00:00:00Z"


def test_parse_start_rejects_non_utc() -> None:
    with pytest.raises(ValueError):
        parse_start("2026-10-01T02:00:00+02:00")


def test_parse_start_accepts_z() -> None:
    assert parse_start("2026-10-01T00:00:00Z") == START


def test_generate_all_events_are_sorted() -> None:
    seed_data = generate_seed(42, COMPANY_SPECS)

    events = generate_all_events(
        seed_data,
        START,
        timedelta(hours=1),
    )

    times = [event.event_time for event in events]

    assert times == sorted(times)
