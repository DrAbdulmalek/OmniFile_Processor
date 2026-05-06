import json
from pathlib import Path

from mobile_review import server


def test_export_dataset_route_creates_jsonl(tmp_path: Path, monkeypatch):
    corrections_path = tmp_path / "ocr_corrected.json"
    corrections_payload = [
        {
            "id": "blk-1",
            "original_text": "السللام عليكم",
            "corrected_text": "السلام عليكم",
            "bbox": [10, 20, 30, 40],
        }
    ]
    corrections_path.write_text(json.dumps(corrections_payload, ensure_ascii=False), encoding="utf-8")

    monkeypatch.setattr(server, "OUTPUT_FILE", str(corrections_path))

    client = server.app.test_client()
    output_prefix = tmp_path / "exports" / "review_dataset"
    response = client.get(f"/export_dataset?output={output_prefix}")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "success"
    assert payload["summary"]["total_records"] == 1
    assert output_prefix.with_suffix(".jsonl").exists()
    assert output_prefix.with_name(output_prefix.name + "_summary.json").exists()


def test_save_endpoint_rejects_invalid_json():
    client = server.app.test_client()
    response = client.post("/save", data="not-json", content_type="application/json")
    assert response.status_code == 400
    assert response.get_json()["status"] == "error"
