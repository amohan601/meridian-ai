import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# Make the backend packages (agent, rag, config, ...) importable the same way the app runs them.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Tests write to a throwaway data folder, not the app's real .meridian/ store.
# Must be set before the app's settings are loaded by the imports below.
TEST_DATA_DIR = tempfile.mkdtemp(prefix="meridian_tests_")
os.environ["LOCAL_DATA_DIR"] = TEST_DATA_DIR

from rag.data_ingestion import ingest_pdf  # noqa: E402

SAMPLE_DOCS = Path(__file__).resolve().parents[2] / "sample_docs"


@pytest.fixture(scope="session", autouse=True)
def test_data_dir():
    """Delete the throwaway data folder once the whole test run is finished."""
    yield TEST_DATA_DIR
    shutil.rmtree(TEST_DATA_DIR, ignore_errors=True)


@pytest.fixture(scope="session")
def indexed_documents(test_data_dir):
    """Index the sample PDFs once per test run, so the vector store is never empty on a fresh machine."""
    for pdf in sorted(SAMPLE_DOCS.glob("*.pdf")):
        ingest_pdf(str(pdf), pdf.name)
