# Archival Status — OmniFile_Processor

> ✅ **This repository is archived on GitHub as of 2026-07-31.**

## Why archived

All functionality has been migrated to the core platform:
👉 **[Omni-Medical-Suite](https://github.com/DrAbdulmalek/omni-medical-suite)**

The last commit (`fd7488b`) was titled "chore: final prune - remove
modules duplicated in omni-medical-suite" — confirming the redundancy
was already addressed at the code level.

## Verification of redundancy

Before archival, the following were checked:

1. **Code-level prune** — the final commit removed modules duplicated
   in omni-medical-suite. Confirmed via `git log -1 --format="%B"`.
2. **README already deprecated** — the README header says
   "LEGACY (Deprecated)" and "Archived on 2026-06-25".
3. **No unique testable value** — the OmniFile_Processor `pyproject.toml`
   declares `version = "4.3.0"` but no tag exists, and the modules
   that would have been unique (OCR engines, NLP pipeline) have been
   migrated to Omni's `src/` and `packages/`.

## What is preserved (read-only)

- The README, CHANGELOG, and historical source code remain accessible
  for reference.
- The HuggingFace Space metadata at the top of README.md is kept as-is
  (the Space itself is a separate concern).

## Verification

- GitHub archive flag: `true` (verified via API on 2026-07-31).
- README already declared deprecation; this doc confirms the GitHub
  state now matches the README claim.
- No further changes will be made to this repo. To revive it, un-archive
  via GitHub Settings → Danger Zone → un-archive.

## Reference

- `ECOSYSTEM_STATE.md` in `repo-sync-toolkit` — ecosystem state.
