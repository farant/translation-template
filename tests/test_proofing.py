from scripts import proofing


def test_load_flags_empty_when_no_file(tmp_path):
    assert proofing.load_flags(tmp_path) == []


def test_add_flag_appends_and_persists(tmp_path):
    proofing.add_flag(tmp_path, "001", 3, "OCR dropped a line")
    proofing.add_flag(tmp_path, "002", 0, "wrong verse number")
    flags = proofing.load_flags(tmp_path)
    assert flags == [
        {"page": "001", "block": 3, "note": "OCR dropped a line"},
        {"page": "002", "block": 0, "note": "wrong verse number"},
    ]


def test_add_flag_round_trips_through_disk(tmp_path):
    proofing.add_flag(tmp_path, "005", 1, "faded")
    # fresh read proves it was written, not just held in memory
    assert proofing.load_flags(tmp_path)[0]["note"] == "faded"
