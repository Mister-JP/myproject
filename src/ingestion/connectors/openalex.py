from __future__ import annotations

from typing import Iterable, Optional

import requests

from .base import Connector, PDFRef, PaperMetadata, QuerySpec


BASE_URL = "https://api.openalex.org/works"


class OpenAlexConnector(Connector):
    source_name = "openalex"

    def search(self, query: QuerySpec) -> Iterable[PaperMetadata]:
        params: dict[str, str] = {
            "search": " ".join(query.keywords) if query.keywords else "",
            "per_page": str(query.max_results or 10),
        }
        filters: list[str] = []
        if query.authors:
            # OpenAlex filter by author.display_name.search
            filters.append("author.display_name.search:%s" % (" ".join(query.authors)))
        if query.year_start is not None or query.year_end is not None:
            start = query.year_start or "1900"
            end = query.year_end or "2100"
            filters.append(f"from_publication_date:{start}-01-01")
            filters.append(f"to_publication_date:{end}-12-31")
        if filters:
            params["filter"] = ",".join(filters)

        r = requests.get(BASE_URL, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        for item in data.get("results", [])[: query.max_results or 10]:
            doi = item.get("doi")
            title = item.get("title") or item.get("display_name") or ""
            authors = [a.get("author", {}).get("display_name", "") for a in item.get("authorships", [])]
            abstract = item.get("abstract") or None
            license_str = None
            oa_info = item.get("open_access", {})
            if isinstance(oa_info, dict):
                license_str = oa_info.get("license")
            concepts = [c.get("display_name", "") for c in item.get("concepts", [])]
            # Prefer explicit publication year when present, then try date fields
            year = None
            try:
                if item.get("publication_year") is not None:
                    year = int(item["publication_year"])  # type: ignore[arg-type]
                elif item.get("publication_date"):
                    year = int(str(item["publication_date"])[:4])
                elif item.get("from_publication_date"):
                    year = int(str(item["from_publication_date"])[:4])
            except Exception:  # noqa: BLE001
                year = None
            citation_count = item.get("cited_by_count")
            external_id = item.get("id")

            yield PaperMetadata(
                source=self.source_name,
                external_id=external_id,
                doi=doi,
                title=title,
                authors=[a for a in authors if a],
                abstract=abstract,
                license=license_str,
                pdf_url=None,  # OpenAlex may provide OA URLs via best_oa_location
                year=year,
                venue=(item.get("host_venue", {}) or {}).get("display_name"),
                concepts=[c for c in concepts if c],
                citation_count=citation_count,
            )

    def fetch_pdf(self, item: PaperMetadata) -> Optional[PDFRef]:
        # Try to use best_oa_location if present when metadata originated from OpenAlex
        return None


