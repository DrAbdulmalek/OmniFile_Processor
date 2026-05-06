### `train/data_mixing.py` (تحديث)

> 🤔 *سؤال رياضي: لماذا نستبدل `drift * 1.5` بدالة لوجستية؟*
> لأن الانزياحات المفاجئة (مثلاً: إضافة وثائق قانونية بعد طبية) لا تتطلب قفزة خطية في الخلط، بل انتقالاً سلساً يتشبع عند حد أقصى لمنع إغراق النموذج ببيانات قديمة.

```python
import math
import json
from pathlib import Path
from typing import List, Dict
from collections import Counter

class DataMixingManager:
    def __init__(
        self,
        archive_dir: str = "data_archive",
        min_ratio: float = 0.05,
        max_ratio: float = 0.35,
        k_steepness: float = 12.0,
        x0_midpoint: float = 0.4
    ):
        self.archive = Path(archive_dir)
        self.archive.mkdir(exist_ok=True)
        self.min_ratio, self.max_ratio = min_ratio, max_ratio
        self.k, self.x0 = k_steepness, x0_midpoint
        self.index = self._load_index()

    def _load_index(self) -> Dict:
        idx = self.archive / "index.json"
        return json.loads(idx.read_text(encoding="utf-8")) if idx.exists() else {"versions": [], "last_drift": 0.0}

    def compute_mix_ratio(self, drift: float) -> float:
        """دالة لوجستية سلسة: تحول الانزياح (0..1) إلى نسبة خلط محدودة"""
        sigmoid = 1.0 / (1.0 + math.exp(-self.k * (drift - self.x0)))
        ratio = self.min_ratio + (self.max_ratio - self.min_ratio) * sigmoid
        return max(self.min_ratio, min(self.max_ratio, ratio))

    def compute_drift(self, new_dist: Dict[str, int]) -> float:
        if not self.index["versions"]: return 0.0
        old = self.index["versions"][-1]["distribution"]
        all_types = set(list(old.keys()) + list(new_dist.keys()))
        t_new = sum(new_dist.values()) or 1
        t_old = sum(old.values()) or 1
        # مسافة L1 معيارة (0..1)
        drift = sum(abs(new_dist.get(k, 0)/t_new - old.get(k, 0)/t_old) for k in all_types) / len(all_types)
        self.index["last_drift"] = drift
        return drift

    def mix_iterative(self, new_data_path: str, new_dist: Dict) -> List[Dict]:
        new_data = json.loads(Path(new_data_path).read_text(encoding="utf-8"))
        drift = self.compute_drift(new_dist)
        mix_ratio = self.compute_mix_ratio(drift)

        target_old = int(len(new_data) * mix_ratio / (1.0 - mix_ratio + 1e-9))
        old_samples = []

        for ver in reversed(self.index["versions"]):
            if target_old <= 0: break
            ver_data = json.loads(Path(ver["path"]).read_text(encoding="utf-8"))
            stratified = self._stratified_sample(ver_data, target_old)
            old_samples.extend(stratified)
            target_old -= len(stratified)

        mixed = new_data + old_samples
        import random; random.shuffle(mixed)

        print(f"📊 خلط لوجستي: جديد={len(new_data)} | قديم={len(old_samples)} | انزياح={drift:.2%} | نسبة={mix_ratio:.0%}")
        return mixed

    def _stratified_sample(self, data: List[Dict], n: int) -> List[Dict]:
        if not data: return []
        groups = {}
        for d in data: groups.setdefault(d.get("block_type", "unknown"), []).append(d)
        sampled = []
        for k, items in groups.items():
            cnt = max(1, int(n * len(items) / len(data)))
            sampled.extend(random.sample(items, min(cnt, len(items))))
        return sampled[:n]

    def archive_version(self, dataset_path: str, version_tag: str):
        data = json.loads(Path(dataset_path).read_text(encoding="utf-8"))
        dist = Counter([d.get("block_type", "unknown") for d in data])
        self.index["versions"].append({
            "tag": version_tag, "path": str(Path(dataset_path).absolute()),
            "size": len(data), "distribution": dict(dist),
            "archived_at": datetime.now().isoformat()
        })
        (self.archive / "index.json").write_text(json.dumps(self.index, ensure_ascii=False, indent=2))
```

---
