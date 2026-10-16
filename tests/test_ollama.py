import pytest
from src.worker.ollama_client import OllamaWorkerClient


@pytest.mark.ollama
def test_ollama_connection():
    worker = OllamaWorkerClient()
    conn_info = worker.check_connection()
    assert conn_info["ollama_connected"] is True, f"Ollama connection failed: {conn_info.get('error')}"
    assert conn_info["model_available"] is True, f"Target model {worker.model} not found in Ollama"
