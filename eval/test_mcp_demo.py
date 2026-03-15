"""
Script de demonstração do MCP — para testar na apresentação.

Pré-requisito: subir o servidor com `python src/mcp/server.py`
Depois: python eval/test_mcp_demo.py
"""

import httpx

BASE = "http://localhost:8000"


def main():
    print("=== Teste MCP EduRAG ===\n")

    # 1. Health
    try:
        r = httpx.get(f"{BASE}/health", timeout=5)
        data = r.json()
        print(f"1. Health: {data['status']} — tools: {data['allowed_tools']}")
    except Exception as e:
        print(f"1. Health: ERRO — {e}")
        print("   Servidor rodando? Execute: python src/mcp/server.py")
        return

    # 2. List tools
    try:
        r = httpx.get(f"{BASE}/tools", timeout=5)
        tools = r.json()["tools"]
        print(f"\n2. Tools disponíveis ({len(tools)}):")
        for t in tools:
            print(f"   - {t['name']}: {t['description']}")
    except Exception as e:
        print(f"2. Tools: ERRO — {e}")
        return

    # 3. Get info
    try:
        r = httpx.get(f"{BASE}/tools/get_info", timeout=5)
        info = r.json()
        print(f"\n3. Sistema: {info['sistema']}")
        print(f"   Corpus: {len(info['corpus'])} documentos")
    except Exception as e:
        print(f"3. Get info: ERRO — {e}")

    # 4. Search (requer corpus ingerido)
    try:
        r = httpx.post(
            f"{BASE}/tools/search_docs",
            json={"query": "BNCC alfabetização", "top_k": 2},
            timeout=30,
        )
        if r.status_code == 200:
            results = r.json().get("results", [])
            print(f"\n4. Search 'BNCC alfabetização': {len(results)} resultados")
            for i, doc in enumerate(results[:5], 1):
                preview = doc.get("content", "")[:80] + "..." if len(doc.get("content", "")) > 80 else doc.get("content", "")
                print(f"   - {i}: {preview}")
        else:
            print(f"\n4. Search: status {r.status_code}")
    except Exception as e:
        print(f"\n4. Search: ERRO — {e}")

    print("\n=== MCP OK ===")


if __name__ == "__main__":
    main()
