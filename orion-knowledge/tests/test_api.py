import pytest
from fastapi.testclient import TestClient

from app import knowledge
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    monkeypatch.setattr(knowledge, "DB_PATH", tmp_path / "orion-tests.db")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def test_ingest_retrieve_and_cite():
    result = client.post("/api/documents", json={
        "title": "Manual Interno - Controle de Estoque",
        "content": (
            "Os produtos refrigerados devem ser recebidos, identificados e armazenados. "
            "O responsável pelo estoque registra temperatura e lote no sistema. "
            "Sempre verificar as datas de validade antes de liberar a expedição. "
            "As diferenças são encaminhadas para análise da coordenação."
        ),
    })
    assert result.status_code == 201, result.text
    body = result.json()
    assert body["chunks"] >= 1

    answer = client.post("/api/ask", json={"question": "Como registrar temperatura e lote?"})
    assert answer.status_code == 200
    payload = answer.json()
    assert payload["mode"] == "retrieval_only"
    assert payload["sources"]
    assert payload["sources"][0]["document"] == "Manual Interno - Controle de Estoque"
    assert payload["sources"][0]["document_id"] == body["id"]
    assert payload["sources"][0]["score"] > 0

    docs = client.get("/api/documents").json()
    assert len(docs) == 1
    assert client.delete(f"/api/documents/{body['id']}").status_code == 200
    assert client.post("/api/ask", json={"question": "Qual é o lote?"}).json()["mode"] == "no_evidence"


def test_no_hallucination_without_documents():
    result = client.post("/api/ask", json={"question": "Qual é o protocolo de incêndio?"})
    assert result.status_code == 200
    assert result.json()["sources"] == []
    assert result.json()["mode"] == "no_evidence"


def test_long_document_chunk_overlap():
    content = " ".join(f"palavra{i}" for i in range(300))
    chunks = knowledge.chunk_text(content)
    assert len(chunks) >= 3
    assert chunks[0].split()[-25:] == chunks[1].split()[:25]


def test_validation_and_not_found():
    bad = client.post("/api/documents", json={"title": "x", "content": "curto"})
    assert bad.status_code == 422
    assert client.delete("/api/documents/nao-existe").status_code == 404
    assert client.post("/api/ask", json={"question": "a"}).status_code == 422


def test_status():
    data = client.get("/api/status").json()
    assert data["mode"] == "retrieval_only"
    assert data["documents"] == 0
