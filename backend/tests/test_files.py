"""
اختبارات رفع الملفات: النوع الفعلي، الحجم، الملكية، والتنزيل.
"""
import asyncio
import io
import struct
import zipfile

import pytest

from app.config import settings as app_settings
from app.models.file_attachment import FileAttachment
from app.routers import files as files_router
from app.services.malware_scanner import MalwareDetected, MalwareScannerUnavailable

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


def test_upload_rejects_malware_and_removes_temporary_file(
    client, tmp_path, monkeypatch, db_session
):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(app_settings, "MALWARE_SCAN_ENABLED", True)

    async def infected_scan(_path):
        raise MalwareDetected("test signature")

    monkeypatch.setattr(files_router, "scan_file_with_clamav", infected_scan)
    token = _register_and_login(client, "infected-upload@example.com")
    response = client.post(
        "/files/upload",
        files={"file": ("payload.png", PNG_BYTES, "image/png")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422
    assert not [path for path in tmp_path.rglob("*") if path.is_file()]
    assert db_session.query(FileAttachment).count() == 0


def test_upload_fails_closed_when_malware_scanner_is_unavailable(
    client, tmp_path, monkeypatch, db_session
):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(app_settings, "MALWARE_SCAN_ENABLED", True)

    async def unavailable_scan(_path):
        raise MalwareScannerUnavailable("test scanner outage")

    monkeypatch.setattr(files_router, "scan_file_with_clamav", unavailable_scan)
    token = _register_and_login(client, "scanner-outage@example.com")
    response = client.post(
        "/files/upload",
        files={"file": ("payload.png", PNG_BYTES, "image/png")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 503
    assert not [path for path in tmp_path.rglob("*") if path.is_file()]
    assert db_session.query(FileAttachment).count() == 0


def test_upload_runs_malware_scan_before_persisting_attachment(
    client, tmp_path, monkeypatch
):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(app_settings, "MALWARE_SCAN_ENABLED", True)
    scanned_paths = []

    async def clean_scan(path):
        scanned_paths.append(path)
        assert path.is_file()

    monkeypatch.setattr(files_router, "scan_file_with_clamav", clean_scan)
    token = _register_and_login(client, "clean-upload@example.com")
    response = client.post(
        "/files/upload",
        files={"file": ("clean.png", PNG_BYTES, "image/png")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    assert len(scanned_paths) == 1
    assert scanned_paths[0].exists()


@pytest.mark.parametrize(
    ("setting_name", "setting_value"),
    [("MAX_USER_STORAGE_MB", 0), ("MAX_USER_FILES", 0)],
)
def test_upload_enforces_per_user_storage_and_file_count_quotas(
    client, tmp_path, monkeypatch, setting_name, setting_value
):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(app_settings, setting_name, setting_value)
    token = _register_and_login(client, f"quota-{setting_name.lower()}@example.com")
    response = client.post(
        "/files/upload",
        files={"file": ("quota.png", PNG_BYTES, "image/png")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 413
    assert not [path for path in tmp_path.rglob("*") if path.is_file()]


def _run_fake_clamd(reply: bytes, file_bytes: bytes, scanner_error=None):
    async def scenario():
        received = bytearray()

        async def handle(reader, writer):
            try:
                command = await reader.readuntil(b"\\0")
                assert command == b"zINSTREAM\\0"
                while True:
                    length = struct.unpack("!I", await reader.readexactly(4))[0]
                    if length == 0:
                        break
                    received.extend(await reader.readexactly(length))
                writer.write(reply + b"\\0")
                await writer.drain()
            finally:
                writer.close()
                await writer.wait_closed()

        server = await asyncio.start_server(handle, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        monkeypatch = scanner_error["monkeypatch"]
        monkeypatch.setattr(app_settings, "CLAMAV_HOST", "127.0.0.1")
        monkeypatch.setattr(app_settings, "CLAMAV_PORT", port)
        monkeypatch.setattr(app_settings, "CLAMAV_TIMEOUT_SECONDS", 2)
        file_path = scanner_error["path"]
        file_path.write_bytes(file_bytes)
        try:
            await files_router.scan_file_with_clamav(file_path)
        finally:
            server.close()
            await server.wait_closed()
        return bytes(received)

    return asyncio.run(scenario())


def test_clamav_instream_protocol_sends_bounded_file_chunks_and_accepts_clean_result(
    tmp_path, monkeypatch
):
    from app.services.malware_scanner import scan_file_with_clamav

    payload = b"sample-file-content" * 5000
    path = tmp_path / "clean.bin"
    path.write_bytes(payload)

    async def scenario():
        received = bytearray()

        async def handle(reader, writer):
            command = await reader.readuntil(b"\\0")
            assert command == b"zINSTREAM\\0"
            while True:
                length = struct.unpack("!I", await reader.readexactly(4))[0]
                if length == 0:
                    break
                assert length <= 64 * 1024
                received.extend(await reader.readexactly(length))
            writer.write(b"stream: OK\\0")
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        server = await asyncio.start_server(handle, "127.0.0.1", 0)
        monkeypatch.setattr(app_settings, "CLAMAV_HOST", "127.0.0.1")
        monkeypatch.setattr(
            app_settings, "CLAMAV_PORT", server.sockets[0].getsockname()[1]
        )
        monkeypatch.setattr(app_settings, "CLAMAV_TIMEOUT_SECONDS", 2)
        try:
            await scan_file_with_clamav(path)
        finally:
            server.close()
            await server.wait_closed()

    asyncio.run(scenario())
    assert bytes(received) == payload


def test_clamav_instream_protocol_rejects_infected_result(tmp_path, monkeypatch):
    from app.services.malware_scanner import scan_file_with_clamav

    path = tmp_path / "infected.bin"
    path.write_bytes(b"eicar-test-pattern")

    async def scenario():
        async def handle(reader, writer):
            await reader.readuntil(b"\\0")
            while True:
                length = struct.unpack("!I", await reader.readexactly(4))[0]
                if length == 0:
                    break
                await reader.readexactly(length)
            writer.write(b"stream: Eicar-Test-Signature FOUND\\0")
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        server = await asyncio.start_server(handle, "127.0.0.1", 0)
        monkeypatch.setattr(app_settings, "CLAMAV_HOST", "127.0.0.1")
        monkeypatch.setattr(
            app_settings, "CLAMAV_PORT", server.sockets[0].getsockname()[1]
        )
        monkeypatch.setattr(app_settings, "CLAMAV_TIMEOUT_SECONDS", 2)
        try:
            with pytest.raises(MalwareDetected):
                await scan_file_with_clamav(path)
        finally:
            server.close()
            await server.wait_closed()

    asyncio.run(scenario())


def test_clamav_instream_protocol_fails_closed_on_scanner_error(tmp_path, monkeypatch):
    from app.services.malware_scanner import scan_file_with_clamav

    path = tmp_path / "scanner-error.bin"
    path.write_bytes(b"sample")

    async def scenario():
        async def handle(reader, writer):
            await reader.readuntil(b"\\0")
            while True:
                length = struct.unpack("!I", await reader.readexactly(4))[0]
                if length == 0:
                    break
                await reader.readexactly(length)
            writer.write(b"stream: INSTREAM size limit exceeded. ERROR\\0")
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        server = await asyncio.start_server(handle, "127.0.0.1", 0)
        monkeypatch.setattr(app_settings, "CLAMAV_HOST", "127.0.0.1")
        monkeypatch.setattr(
            app_settings, "CLAMAV_PORT", server.sockets[0].getsockname()[1]
        )
        monkeypatch.setattr(app_settings, "CLAMAV_TIMEOUT_SECONDS", 2)
        try:
            with pytest.raises(MalwareScannerUnavailable):
                await scan_file_with_clamav(path)
        finally:
            server.close()
            await server.wait_closed()

    asyncio.run(scenario())
