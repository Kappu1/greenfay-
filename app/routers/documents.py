from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os, uuid, mimetypes

from app.database import get_db
from app.models import DocumentAttachment, User
from app.auth import current_user, audit

router = APIRouter()

UPLOAD_DIR = os.getenv('UPLOAD_DIR', os.path.join(os.getcwd(), 'uploads'))
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.webp', '.xlsx', '.xls', '.csv', '.docx', '.doc'}
MAX_FILE_SIZE = int(os.getenv('MAX_UPLOAD_SIZE', 10 * 1024 * 1024))  # 10 MB

@router.post('/documents/upload')
async def upload_document(
    file: UploadFile = File(...),
    entity_type: str = Form(...),
    entity_id: int = Form(...),
    document_type: str = Form(...),
    notes: str = Form(''),
    db: Session = Depends(get_db),
    user: User = Depends(current_user)
):
    orig_name = file.filename or 'document'
    _, ext = os.path.splitext(orig_name.lower())
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"File type '{ext}' is not permitted. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(400, f"File exceeds maximum allowed size of {MAX_FILE_SIZE // (1024 * 1024)} MB")

    doc_uuid = str(uuid.uuid4())
    stored_name = f"{doc_uuid}{ext}"
    dest_path = os.path.join(UPLOAD_DIR, stored_name)

    with open(dest_path, 'wb') as f:
        f.write(contents)

    mime = file.content_type or mimetypes.guess_type(orig_name)[0] or 'application/octet-stream'

    doc = DocumentAttachment(
        document_id=doc_uuid,
        entity_type=entity_type,
        entity_id=entity_id,
        document_type=document_type,
        original_filename=orig_name,
        stored_filename=stored_name,
        mime_type=mime,
        file_size_bytes=len(contents),
        uploaded_by_id=user.id,
        notes=notes
    )
    db.add(doc)
    db.flush()
    audit(db, user, 'DocumentAttachment', doc.id, 'UPLOAD', f"Uploaded {orig_name} for {entity_type} #{entity_id}", module='Documents')
    db.commit()

    return {
        'id': doc.id,
        'document_id': doc.document_id,
        'filename': doc.original_filename,
        'size': doc.file_size_bytes,
        'document_type': doc.document_type
    }

@router.get('/documents/{id}/download')
def download_document(id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    doc = db.get(DocumentAttachment, id)
    if not doc:
        raise HTTPException(404, 'Document not found')

    file_path = os.path.join(UPLOAD_DIR, doc.stored_filename)
    if not os.path.exists(file_path):
        raise HTTPException(404, 'Stored file missing from disk')

    return FileResponse(
        path=file_path,
        filename=doc.original_filename,
        media_type=doc.mime_type
    )

@router.get('/documents/{entity_type}/{entity_id}')
def list_entity_documents(entity_type: str, entity_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    docs = db.query(DocumentAttachment).filter(
        DocumentAttachment.entity_type == entity_type,
        DocumentAttachment.entity_id == entity_id
    ).order_by(DocumentAttachment.id.desc()).all()

    return [
        {
            'id': d.id,
            'document_id': d.document_id,
            'document_type': d.document_type,
            'filename': d.original_filename,
            'size': d.file_size_bytes,
            'mime_type': d.mime_type,
            'uploaded_at': str(d.uploaded_at),
            'notes': d.notes
        }
        for d in docs
    ]

@router.delete('/documents/{id}')
def delete_document(id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    doc = db.get(DocumentAttachment, id)
    if not doc:
        raise HTTPException(404, 'Document not found')

    if user.role != 'admin' and doc.uploaded_by_id != user.id:
        raise HTTPException(403, 'Cannot delete document uploaded by another user')

    file_path = os.path.join(UPLOAD_DIR, doc.stored_filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass

    audit(db, user, 'DocumentAttachment', doc.id, 'DELETE', f"Deleted {doc.original_filename}", module='Documents')
    db.delete(doc)
    db.commit()
    return {'ok': True}
