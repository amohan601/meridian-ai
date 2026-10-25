from pathlib import Path

from rag.data_ingestion import ingest_pdf

SAMPLE_PDF = Path(__file__).resolve().parents[3] / "sample_docs" / "aldermoor_procurement_policy.pdf"


def test_ingest_pdf_loads_and_indexes_real_pdf():
    result = ingest_pdf(str(SAMPLE_PDF), SAMPLE_PDF.name)

    assert result["pages"] > 0
    assert result["chunks"] > 0
