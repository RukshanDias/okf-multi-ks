# Workflow B — Conversation source

Use when the user says things like: *"add what we discussed about git to OKF"* — no URL; source is chat / notes.

```
- [ ] Confirm topic scope, KS root, concept type/location
- [ ] Review conversation for the relevant content only
- [ ] Discover Intra-KS peers via that KS's index.md
- [ ] Cursor: write curated body to temp file (Intra-KS See also only)
- [ ] Run ingest_okf_concept.py --body-file … (no --url)  # mints id
- [ ] For Cross-KS peers: okf associate … --source ingest
- [ ] Run okf check
```

## Persist

```bash
.venv/Scripts/python.exe scripts/ingest_okf_concept.py \
  --out BUNDLE_ROOT \
  --type Learning \
  --title "Git Workflow Notes" \
  --concept-id git-workflow-notes \
  --description "Summarizes git practices discussed in conversation." \
  --tag git \
  --body-file path/to/body.md
```

## Example

```
/okf-ingest add the things we discuss about git to OKF as a Learning
→ --out <ks_library>/personal, concept-id: git-workflow-notes
→ okf associate … --source ingest  (only if Cross-KS peers agreed)
→ okf check
```
