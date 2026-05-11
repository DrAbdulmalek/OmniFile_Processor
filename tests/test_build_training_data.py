import json
from pathlib import Path

from tools.build_training_data import build_dataset, write_outputs


def test_build_dataset_extracts_changed_and_unchanged_records():
    payload = {
        "items": [
            {
                "id": "a1",
                "original_text": "مرحبا",
                "corrected_text": "مرحبا",
                "bbox": [1, 2, 3, 4],
                "page": 1,
            },
            {
                "id": "a2",
                "ocr_text": "السللام",
                "reviewed_text": "السلام",
                "bounding_box": [5, 6, 7, 8],
                "page_num": 2,
            },
        ]
    }

    records, summary = build_dataset(payload)

    assert len(records) == 2
    assert summary["total_records"] == 2
    assert summary["changed_records"] == 1
    assert records[0]["changed"] is False
    assert records[1]["changed"] is True
    assert records[1]["bbox"] == [5, 6, 7, 8]
    assert records[1]["page"] == 2


def test_write_outputs_creates_jsonl_and_summary(tmp_path: Path):
    records = [{"id": "x1", "ocr_text": "a", "corrected_text": "b", "changed": True}]
    summary = {"total_records": 1, "changed_records": 1, "unchanged_records": 0, "change_ratio": 1.0}
    output = tmp_path / "dataset" / "review_dataset"

    write_outputs(records, summary, output)

    jsonl_path = output.with_suffix(".jsonl")
    summary_path = output.with_name(output.name + "_summary.json")

    assert jsonl_path.exists()
    assert summary_path.exists()
    assert json.loads(summary_path.read_text(encoding="utf-8"))["total_records"] == 1
    assert '"id": "x1"' in jsonl_path.read_text(encoding="utf-8")
