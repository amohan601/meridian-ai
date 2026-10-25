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