# Design Spec: Material Upload & Listing Pipeline (Phase 2)

**Date:** 2026-03-15
**Issue:** jking-ai/vision-first-study-buddy#4
**Status:** Approved

---

## Overview

Implement the material upload, validation, and listing pipeline for Vision-First Study Buddy. Students can upload study materials (images, PDFs, epubs) via the API, which are stored in Firebase Storage and retrievable with signed preview URLs.

---

## Architecture

### Components

1. **`MaterialProcessor`** — validates files, extracts metadata, prepares Gemini content parts
2. **`StorageClient`** (extended) — add `time_created`/`material_id` to `list_materials()`, add `get_material_blobs()` for single-material lookup
3. **`upload.py` router** — `POST /api/v1/materials/upload`
4. **`materials.py` router** — `GET /api/v1/materials`, `GET /api/v1/materials/{id}`

---

## Data Flow

### Upload
```
Client --(multipart)--> POST /api/v1/materials/upload
  -> MaterialProcessor.validate_file() [MIME + size]
  -> MaterialProcessor.extract_metadata() [filename, content_type, size_bytes]
  -> generate material_id (mat_ + uuid4()[:8])
  -> StorageClient.upload_file(bytes, materials/{id}/{filename}, content_type)
  -> Build MaterialResponse (id, filename, content_type, size_bytes, storage_url, uploaded_at=now())
  -> Return UploadResponse
```

### List
```
GET /api/v1/materials
  -> StorageClient.list_materials() [returns blobs with time_created, material_id]
  -> Group by material_id (first-level path segment)
  -> Build MaterialResponse per blob
  -> Return MaterialsListResponse
```

### Detail
```
GET /api/v1/materials/{material_id}
  -> StorageClient.get_material_blobs(material_id) [list under materials/{id}/]
  -> 404 if empty
  -> StorageClient.get_signed_url(path) [60-min signed URL]
  -> Return MaterialDetailResponse
```

---

## StorageClient Changes

Update `list_materials()` to include `material_id` (parsed from path) and `time_created` (from blob metadata):

```python
{
    "path": "materials/mat_abc123/photo.jpg",
    "name": "photo.jpg",
    "size": 2048576,
    "content_type": "image/jpeg",
    "material_id": "mat_abc123",          # NEW: parsed from path
    "time_created": datetime(...),         # NEW: from blob.time_created
}
```

Add `get_material_blobs(material_id)` — lists blobs under `materials/{material_id}/`.

---

## MaterialProcessor

### validate_file(filename, content_type, size_bytes)
- Raise `ValueError("UNSUPPORTED_FILE_TYPE: ...")` if content_type not in `SUPPORTED_MIME_TYPES`
- Raise `ValueError("FILE_TOO_LARGE: ...")` if size_bytes > max_file_size_mb * 1024 * 1024

### extract_metadata(filename, content_type, size_bytes)
```python
return {"filename": filename, "content_type": content_type, "size_bytes": size_bytes}
```

### prepare_for_gemini(file_data, content_type)
- **Images** (`image/jpeg`, `image/png`, `image/webp`): base64-encode bytes → `{"inline_data": {"mime_type": ..., "data": base64str}}`
- **PDFs** (`application/pdf`): inline bytes → `{"inline_data": {"mime_type": "application/pdf", "data": base64str}}`
- **Epubs** (`application/epub+zip`): extract text via `ebooklib` + `beautifulsoup4` → `{"text": extracted_text}`

---

## Error Handling

| Condition | HTTP | Error Code |
|---|---|---|
| Unsupported MIME type | 400 | `UNSUPPORTED_FILE_TYPE` |
| File too large (>20 MB) | 400 | `FILE_TOO_LARGE` |
| Material ID not found | 404 | `MATERIAL_NOT_FOUND` |
| Firebase Storage failure | 500 | `STORAGE_ERROR` |

All errors use the existing `ErrorResponse` / `ErrorBody` / `ErrorDetail` structure.

---

## Dependency Injection

Routers use `Depends()` factories for `StorageClient` and `MaterialProcessor`:

```python
def get_storage_client(settings=Depends(get_settings)) -> StorageClient:
    return StorageClient(settings.firebase_storage_bucket)

def get_material_processor(settings=Depends(get_settings)) -> MaterialProcessor:
    return MaterialProcessor(settings)
```

This enables easy test overrides via `app.dependency_overrides`.

---

## Testing Strategy

- **Unit tests** for `MaterialProcessor` — validate MIME/size checks, metadata extraction, Gemini preparation; no Firebase needed
- **Integration tests** for upload/materials endpoints — mock `StorageClient` via `app.dependency_overrides`, test success paths and all error codes
- Update `test_storage_client.py` — account for new `material_id` and `time_created` fields in `list_materials()` return value

---

## Files Modified

| File | Change |
|---|---|
| `backend/app/services/material_processor.py` | Implement all 3 methods |
| `backend/app/services/storage_client.py` | Extend `list_materials()`, add `get_material_blobs()` |
| `backend/app/routers/upload.py` | Implement POST endpoint |
| `backend/app/routers/materials.py` | Implement GET list + GET detail |
| `backend/requirements.txt` | Add `ebooklib`, `beautifulsoup4` |
| `backend/tests/test_material_processor.py` | New test file |
| `backend/tests/test_upload.py` | New test file |
| `backend/tests/test_materials.py` | New test file |
| `backend/tests/test_storage_client.py` | Update for new list_materials fields |
