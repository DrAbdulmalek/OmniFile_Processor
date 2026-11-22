"""إعداد المسارات لاختبارات omnifile-core دون تثبيت الحزمة.

Path bootstrap so `python -m pytest packages/omnifile-core/tests/...`
works from the repository root without installing the package:
- ``packages/omnifile-core``  -> makes ``omnifile_core`` importable
- repository root             -> lets omnifile_core locate the ``modules/`` tree
"""

from pathlib import Path
import sys

# .../packages/omnifile-core/tests/conftest.py
HERE = Path(__file__).resolve().parent          # .../tests
PACKAGE_DIR = HERE.parent                       # .../packages/omnifile-core
REPO_ROOT = HERE.parents[2]                     # .../ (repository root)

for _path in (str(PACKAGE_DIR), str(REPO_ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)
