"""
اختبارات رفع الملفات: النوع الفعلي، الحجم، الملكية، والتنزيل.
"""
import io
import zipfile

from app.config import settings as app_settings

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"test-png-payload"
PDF_BYTES = b"%PDF-1.7\nvalid-test-pdf-payload"


def _register_and_login(client, email="files@example.com", password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    login_response = client.post("/auth/login", json={"email": email, "password": password})
    return login_response.cookies.get("lumen_access")


def _minimal_docx_bytes():
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<document/>")
    return output.getvalue()


def test_upload_file_success(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/files/upload",
        files={"file": ("test.png", PNG_BYTES, "image/png")},
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["original_filename"] == "test.png"
    assert body["content_type"] == "image/png"
    assert body["size_bytes"] == len(PNG_BYTES)


def test_upload_rejects_unsupported_type(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/files/upload",
        files={"file": ("virus.exe", b"binary", "application/x-msdownload")},
        headers=headers,
    )
    assert response.status_code == 415


def test_upload_rejects_mismatched_file_signature_and_removes_partial_file(
    client, tmp_path, monkeypatch
):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    token = _register_and_login(client)
    response = client.post(
        "/files/upload",
        files={"file": ("fake.png", PDF_BYTES, "image/png")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 415
    assert not [path for path in tmp_path.rglob("*") if path.is_file()]


def test_upload_rejects_invalid_docx_container(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    token = _register_and_login(client)
    response = client.post(
        "/files/upload",
        files={"file": ("fake.docx", b"PK not a valid office file", 
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 415
    assert not [path for path in tmp_path.rglob("*") if path.is_file()]


def test_upload_accepts_docx_with_expected_members(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    token = _register_and_login(client)
    response = client.post(
        "/files/upload",
        files={
            "file": (
                "lesson.docx",
                _minimal_docx_bytes(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201


def test_upload_rejects_oversized_file(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(app_settings, "MAX_UPLOAD_SIZE_MB", 0)
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/files/upload",
        files={"file": ("small.png", b"x", "image/png")},
        headers=headers,
    )
    assert response.status_code == 413
    assert not [path for path in tmp_path.rglob("*") if path.is_file()]


def test_list_files(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    client.post(
        "/files/upload",
        files={"file": ("a.pdf", PDF_BYTES, "application/pdf")},
        headers=headers,
    )
    response = client.get("/files", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_download_file_returns_original_bytes(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    upload_response = client.post(
        "/files/upload",
        files={"file": ("note.csv", b"a,b,c\n1,2,3", "text/csv")},
        headers=headers,
    )
    assert upload_response.status_code == 201
    file_id = upload_response.json()["id"]

    download_response = client.get(f"/files/{file_id}", headers=headers)
    assert download_response.status_code == 200
    assert download_response.content == b"a,b,c\n1,2,3"


def test_delete_file(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    upload_response = client.post(
        "/files/upload",
        files={"file": ("a.png", PNG_BYTES, "image/png")},
        headers=headers,
    )
    assert upload_response.status_code == 201
    file_id = upload_response.json()["id"]

    delete_response = client.delete(f"/files/{file_id}", headers=headers)
    assert delete_response.status_code == 204
    assert client.get(f"/files/{file_id}", headers=headers).status_code == 404


def test_cannot_access_other_users_file(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    token_a = _register_and_login(client, "filesowner@example.com")
    upload_response = client.post(
        "/files/upload",
        files={"file": ("secret.pdf", PDF_BYTES, "application/pdf")},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert upload_response.status_code == 201
    file_id = upload_response.json()["id"]

    token_b = _register_and_login(client, "filesintruder@example.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    assert client.get(f"/files/{file_id}", headers=headers_b).status_code == 404
    assert client.delete(f"/files/{file_id}", headers=headers_b).status_code == 404


def test_files_require_authentication(client):
    assert client.get("/files").status_code == 401
    assert (
        client.post("/files/upload", files={"file": ("a.png", b"x", "image/png")}).status_code
        == 401
    )
