## Summary

What changed and why. Link issues if relevant.

## Scope

- [ ] Phase-1 foundations
- [ ] Phase-2 search/index/connectors
- [ ] Phase-3 parsing/summarization
- [ ] DX/docs/infra

## Checklist

- [ ] Tests added/updated as needed
- [ ] `make test` green locally
- [ ] If touching connectors: live runs gated behind `RUN_LIVE=1`, otherwise use/update cassettes
- [ ] License policy respected (`license_permits_pdf_storage`); no restricted PDFs served via API
- [ ] OpenSearch index mapping unchanged or reindex performed (`make reindex`)
- [ ] Docs updated (`README.md`, `phase-*.md`, or `docs/`)
- [ ] Secrets hygiene: no keys in code or cassettes; `.env.example` updated if needed

## Validation

- [ ] Ingest sample: `python -m ingestion.cli run --query "..." --source ...`
- [ ] Reindex: `make reindex`
- [ ] API smoke: `/search`, `/paper/{id}`, `/summaries`
- [ ] UI smoke: `/ui/search?q=demo` (use `make seed-demo-ui` if needed)
- [ ] Optional: `make bench` p95 under target

## Screenshots / Logs (optional)
