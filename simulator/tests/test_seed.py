from pathlib import Path

from simulator.seed import COMPANY_SPECS, generate_seed, load_seed, write_seed


def all_devices(seed_data):
    return [d for c in seed_data.companies for loc in c.locations for d in loc.devices]


def test_same_seed_gives_identical_output():
    assert generate_seed(42, COMPANY_SPECS) == generate_seed(42, COMPANY_SPECS)


def test_different_seed_gives_different_ids():
    a = generate_seed(1, COMPANY_SPECS)
    b = generate_seed(2, COMPANY_SPECS)
    assert a.companies[0].id != b.companies[0].id


def test_device_count_matches_specs():
    expected = sum(
        device["count"]
        for company in COMPANY_SPECS
        for location in company["locations"]
        for device in location["devices"]
    )
    assert len(all_devices(generate_seed(42, COMPANY_SPECS))) == expected


def test_all_ids_are_unique():
    seed_data = generate_seed(42, COMPANY_SPECS)
    ids = [c.id for c in seed_data.companies]
    ids += [loc.id for c in seed_data.companies for loc in c.locations]
    ids += [d.id for d in all_devices(seed_data)]
    assert len(ids) == len(set(ids))


def test_seed_survives_write_and_load(tmp_path: Path) -> None:
    original = generate_seed(42, COMPANY_SPECS)
    path = tmp_path / "seed.json"

    write_seed(original, path)
    loaded = load_seed(path)

    assert loaded == original
