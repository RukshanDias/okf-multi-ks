# Workflow A — URL source

Use when the knowledge source is a web page, blog, or guide (user provides a URL).

```
- [ ] Confirm URL, KS root, concept type/location
- [ ] Fetch via fetch_url (Python)
- [ ] Discover Intra-KS peers via that KS's index.md
- [ ] Cursor: write curated body to temp file (Intra-KS See also only)
- [ ] Run ingest_okf_concept.py --url … --body-file …  # mints id
- [ ] For Cross-KS peers: okf associate … --source ingest
- [ ] Run okf check
```

## Fetch

```bash
.venv/Scripts/python.exe -c "
from reference_agent.web.fetcher import fetch_and_parse
p = fetch_and_parse('SEED_URL')
print(p.title)
print(p.markdown[:8000])
"
```

## Persist

```bash
.venv/Scripts/python.exe scripts/ingest_okf_concept.py \
  --url "SEED_URL" \
  --out BUNDLE_ROOT \
  --type Learning \
  --title "My Title" \
  --concept-id my-slug \
  --description "One sentence summary." \
  --tag topic-tag \
  --body-file path/to/body.md
```

## Example

```
/okf-ingest add https://example.com/guide to OKF as a Document
→ --out <ks_library>/work, concept-id: example-guide
→ okf associate … --source ingest  (only if Cross-KS peers agreed)
→ okf check
```
