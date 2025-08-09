from .arxiv import ArxivConnector
from .openalex import OpenAlexConnector
from .base import Connector, PaperMetadata, QuerySpec, PDFRef

__all__ = [
    "Connector",
    "PaperMetadata",
    "QuerySpec",
    "PDFRef",
    "ArxivConnector",
    "OpenAlexConnector",
]
