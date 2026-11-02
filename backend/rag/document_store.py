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
from exceptions import ConfigurationError
import shutil
from logger import GLOBAL_LOGGER as log
from contextlib import contextmanager
import tempfile

def location() -> str:
    """Human-readable location, shown on the System Status tab."""
    if settings.is_cloud:
        return f"gs://{settings.gcs_bucket_name}/{settings.gcs_prefix}"
    return settings.local_upload_dir

def _bucket():
    """Return a Cloud Storage bucket object, or None if not in cloud mode."""
    if not settings.gcs_bucket_name or not settings.gcp_project_id:
        raise ConfigurationError("APP_MODE=cloud needs GCS_BUCKET_NAME and GCP_PROJECT_ID.")
    from google.cloud import storage

    return storage.Client(project=settings.gcp_project_id).bucket(settings.gcs_bucket_name)

#--------
# save the file to document store
#--------
def save(local_path: str, filename: str) -> str:
    """save the file to document store"""
    log.info(f'document_store.save {filename}')
    filename = os.path.basename(filename)
    log.info(f'document_store.save2 {filename}')
    if settings.is_cloud:   
        blob_name = os.path.join(settings.gcs_prefix, filename)
        log.info(f'blob_name {blob_name}')
        _bucket().blob(blob_name).upload_from_filename(local_path, content_type="application/pdf")
        stored_at = f"gs://{settings.gcs_bucket_name}/{blob_name}"
    else:
        os.makedirs(settings.local_upload_dir, exist_ok=True)
        stored_at = os.path.join(settings.local_upload_dir, filename)
        shutil.copyfile(local_path, stored_at)
    
    log.info(f'document_store.save stored_at {stored_at}')
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
        log.info("Local mode: listing stored PDFs")
        folder = settings.local_upload_dir
        log.info("Listing stored PDFs", folder=folder)
        os.makedirs(folder, exist_ok=True)
        yield (
            (os.path.join(folder, name), f"local://{name}")
            for name in sorted(os.listdir(folder))
            if name.lower().endswith(".pdf")
        )
        return

    tmp_dir = tempfile.mkdtemp()
    try:
        log.info(f"Created temp folder {tmp_dir} for cloud PDFs")   
        def _download():
            for blob in _bucket().list_blobs(prefix=settings.gcs_prefix):
                log.info(f"Found blob {blob.name}")
                if not blob.name.lower().endswith(".pdf"):
                    continue
                local_path = os.path.join(tmp_dir, os.path.basename(blob.name))
                log.info(f"Downloading {blob.name} to {local_path}")
                blob.download_to_filename(local_path)
                yield (local_path, f"gs://{settings.gcs_bucket_name}/{blob.name}")  
        
        log.info("Downloading stored PDFs from cloud")        
        yield _download()   
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)