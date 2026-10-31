"""
Saving the original pdf file to document_store

Where the ORIGINAL PDF files are kept. Which place depends on APP_MODE.

    local  -> a folder on your disk:      .meridian/uploads/
    cloud  -> a Cloud Storage bucket:     gs://<GCS_BUCKET_NAME>/<GCS_PREFIX>

Two operations are all the app needs:
    save(local_path, filename)  keep a copy of an uploaded PDF
    pdfs()                      yield (local_path, source_name) for every stored PDF
"""

import os
from config.settings import settings
import shutil
from logger import GLOBAL_LOGGER as log
from contextlib import contextmanager

def location() -> str:
    """Human-readable location, shown on the System Status tab."""
    return settings.local_upload_dir

#--------
# save the file to document store
#--------
def save(local_path: str, filename: str) -> str:
    """save the file to document store"""
    log.info(f'document_store.save {filename}')
    filename = os.path.basename(filename)
    log.info(f'document_store.save2 {filename}')
    os.makedirs(settings.local_upload_dir, exist_ok=True)
    stored_at = os.path.join(settings.local_upload_dir, filename)
    log.info(f'document_store.save stored_at {stored_at}')
    shutil.copyfile(local_path, stored_at)
    log.info(f"Original file stored {filename}. {stored_at}")
    return stored_at

#--------
# return the stored pds
#--------
@contextmanager
def pdfs():
    """Yield (local_path, source) for every stored PDF.
    Used as a context manager because cloud files are downloaded to a temp folder
    that must be cleaned up afterwards.
    """
    log.info("Inside pdfs")
    if not settings.is_cloud:
        log.info("not cloud")
        folder = settings.local_upload_dir
        log.info("Listing stored PDFs", folder=folder)
        os.makedirs(folder, exist_ok=True)
        yield (
            (os.path.join(folder, name), f"local://{name}")
            for name in sorted(os.listdir(folder))
            if name.lower().endswith(".pdf")
        )
        return
