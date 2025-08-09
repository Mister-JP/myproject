from __future__ import annotations

import json
import time
from typing import Optional

import typer
from dotenv import load_dotenv

from .config import Settings
from .connectors.arxiv import ArxivConnector
from .connectors.openalex import OpenAlexConnector
from .connectors.base import QuerySpec
from .db import Base, create_session_factory, ensure_schema
from .dedup import is_duplicate
from .models import Paper
from .storage import download_pdf_to_storage, ensure_storage_dir


def _init_db(session_factory) -> None:
    # Create tables if not exist
    with session_factory() as session:
        engine = session.get_bind()
        ensure_schema(Base, engine)


def _normalize_license(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    s = raw.strip().lower()
    # simple normalization for CC licenses
    cc_map = {
        "cc-by": "cc-by",
        "cc by": "cc-by",
        "cc-by-sa": "cc-by-sa",
        "cc by-sa": "cc-by-sa",
        "cc0": "cc0",
        "public domain": "public-domain",
    }
    for k, v in cc_map.items():
        if k in s:
            return v
    return s


def main(
    query: str = typer.Option(..., "--query", help="Search query (keywords)"),
    author: Optional[str] = typer.Option(None, "--author", help="Author filter (exact match)"),
    max_results: int = typer.Option(10, "--max-results", help="Max results to fetch"),
    source: str = typer.Option("arxiv", "--source", help="Data source: arxiv|openalex"),
):
    """Run a search against the selected source, store metadata and PDFs (license permitting)."""
    load_dotenv()
    settings = Settings.from_env()
    # Allow CLI override
    if max_results:
        settings.arxiv_max_results = max_results

    session_factory = create_session_factory(settings.database_url)
    _init_db(session_factory)
    ensure_storage_dir(settings.storage_dir)

    connector = ArxivConnector() if source == "arxiv" else OpenAlexConnector()
    spec = QuerySpec(
        keywords=[query] if query else [],
        authors=[author] if author else [],
        max_results=settings.arxiv_max_results,
    )
    records = connector.search(spec)

    stored = 0
    skipped = 0
    errors = 0

    with session_factory() as session:
        for rec in records:
            try:
                # normalize license text early
                rec.license = _normalize_license(rec.license)
                if is_duplicate(
                    session,
                    source=rec.source,
                    doi=rec.doi,
                    external_id=rec.external_id,
                    title=rec.title,
                    authors=rec.authors,
                ):
                    skipped += 1
                    continue

                pdf_path: str | None = None
                # Enforce basic license rule: download PDFs only if license is explicit and not restrictive.
                # For Phase-2 MVP, allow when normalized license is cc-*, cc0, or public-domain. If unknown, skip.
                license_text = rec.license or ""
                allowed_prefixes = ("cc-", "cc0", "public-domain")
                license_permits_download = license_text.startswith(allowed_prefixes)

                if rec.pdf_url and license_permits_download:
                    file_hint = f"{rec.source}-{rec.external_id or ''}".strip("-") + ".pdf"
                    pdf_path = download_pdf_to_storage(
                        rec.pdf_url,
                        storage_dir=settings.storage_dir,
                        file_hint=file_hint,
                        timeout_seconds=settings.request_timeout_seconds,
                    )
                    time.sleep(settings.rate_limit_delay_seconds)

                paper = Paper(
                    source=rec.source,
                    external_id=rec.external_id,
                    doi=rec.doi,
                    title=rec.title,
                    authors={"list": rec.authors},
                    abstract=rec.abstract,
                    license=rec.license,
                    pdf_path=pdf_path,
                    year=rec.year,
                    venue=rec.venue,
                    concepts={"list": rec.concepts or []},
                    citation_count=rec.citation_count,
                )
                session.add(paper)
                session.commit()
                stored += 1
            except Exception as exc:  # noqa: BLE001
                session.rollback()
                errors += 1
                typer.secho(
                    f"Error processing record {rec.external_id}: {exc}", fg=typer.colors.RED
                )

    typer.echo(json.dumps({"stored": stored, "skipped": skipped, "errors": errors}))


if __name__ == "__main__":
    typer.run(main)
