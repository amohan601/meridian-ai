import os

from config.settings import settings
from rag.document_store import save


def test_save_copies_file_into_upload_folder(tmp_path):
    source = tmp_path / "unit_test_upload.pdf"
    source.write_bytes(b"%PDF-1.4 test content")

    stored_at = save(str(source), "unit_test_upload.pdf")

    try:
        assert stored_at == os.path.join(settings.local_upload_dir, "unit_test_upload.pdf")
        assert open(stored_at, "rb").read() == b"%PDF-1.4 test content"
    finally:
        os.remove(stored_at)
