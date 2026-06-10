#!/usr/bin/env python3
"""Test script for ProAiRag Dashboard - runs server and tests all endpoints."""
import asyncio
import httpx
import sys
import threading
import time

def run_server():
    """Run uvicorn in a thread."""
    import uvicorn
    from src.main import create_app
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="error")

async def test_api():
    """Test all API endpoints."""
    base = "http://localhost:8000"
    results = []

    async with httpx.AsyncClient(timeout=30) as c:
        # 1. Health
        try:
            r = await c.get(f"{base}/health")
            results.append(("Health", r.status_code, r.json()))
        except Exception as e:
            results.append(("Health", 0, str(e)))
            print(f"FAIL: {e}")
            return

        # 2. SPA Login page
        try:
            r = await c.get(f"{base}/login")
            results.append(("SPA /login", r.status_code, "has_html=" + str("html" in r.text[:50].lower())))
        except Exception as e:
            results.append(("SPA /login", 0, str(e)))

        # 3. Create tenant
        import time as _time
        ts = int(_time.time())
        tenant_name = f"Test Corp {ts}"
        admin_email = f"admin_{ts}@test.com"
        try:
            r = await c.post(f"{base}/api/tenants/", json={
                "name": tenant_name,
                "admin_email": admin_email,
                "admin_password": "password123",
                "admin_full_name": "Admin User"
            })
            data = r.json()
            results.append(("Create tenant", r.status_code, f"name={data.get('name', '')}"))
        except Exception as e:
            results.append(("Create tenant", 0, str(e)))

        # 4. Login
        try:
            r = await c.post(f"{base}/api/auth/login", json={
                "email": admin_email,
                "password": "password123"
            })
            data = r.json()
            results.append(("Login", r.status_code, f"user={data.get('user', {}).get('email', '')}"))
            jwt = data.get("access_token", "")
        except Exception as e:
            results.append(("Login", 0, str(e)))
            jwt = ""

        # 5. List tenants
        try:
            r = await c.get(f"{base}/api/tenants/")
            data = r.json()
            results.append(("List tenants", r.status_code, f"count={len(data)}"))
        except Exception as e:
            results.append(("List tenants", 0, str(e)))

        # 6. Create department
        try:
            r = await c.post(f"{base}/api/departments/", json={
                "name": "Engineering",
                "description": "Software development"
            }, headers={"Authorization": f"Bearer {jwt}"})
            data = r.json()
            results.append(("Create dept", r.status_code, f"id={data.get('id', '')[:8]}..."))
            dept_id = data.get("id", "")
        except Exception as e:
            results.append(("Create dept", 0, str(e)))
            dept_id = ""

        # 7. Upload document
        try:
            files = {"file": ("test.txt", "This is a test document about vacation policy. Employees get 25 days of paid vacation per year.", "text/plain")}
            data = {"title": "HR Policy", "department_id": dept_id}
            r = await c.post(f"{base}/api/documents/upload", files=files, data=data,
                            headers={"Authorization": f"Bearer {jwt}"})
            d = r.json()
            results.append(("Upload doc", r.status_code, f"title={d.get('title', '')}"))
            doc_id = d.get("id", "")
        except Exception as e:
            results.append(("Upload doc", 0, str(e)))

        # 8. List documents
        try:
            r = await c.get(f"{base}/api/documents/", headers={"Authorization": f"Bearer {jwt}"})
            data = r.json()
            results.append(("List docs", r.status_code, f"count={len(data)}"))
        except Exception as e:
            results.append(("List docs", 0, str(e)))

        # 9. RAG query
        try:
            r = await c.post(f"{base}/api/rag/query", json={
                "query": "How many vacation days do employees get?",
                "top_k": 5
            }, headers={"Authorization": f"Bearer {jwt}"})
            d = r.json()
            answer = d.get("answer", "")[:80]
            results.append(("RAG query", r.status_code, f"answer='{answer}...'"))
        except Exception as e:
            results.append(("RAG query", 0, str(e)))

        # 10. Create chat session
        try:
            r = await c.post(f"{base}/api/chat/sessions/", json={"title": "Test chat"},
                            headers={"Authorization": f"Bearer {jwt}"})
            data = r.json()
            results.append(("Create chat", r.status_code, f"id={data.get('id', '')[:8]}..."))
            session_id = data.get("id", "")
        except Exception as e:
            results.append(("Create chat", 0, str(e)))
            session_id = ""

        # 11. Send chat message
        try:
            r = await c.post(f"{base}/api/chat/sessions/{session_id}/send", json={
                "message": "How many vacation days do we get?"
            }, headers={"Authorization": f"Bearer {jwt}"})
            d = r.json()
            content = d.get("content", "")[:80]
            results.append(("Chat send", r.status_code, f"role={d.get('role')} content='{content}...'"))
        except Exception as e:
            results.append(("Chat send", 0, str(e)))

        # 12. List chat sessions
        try:
            r = await c.get(f"{base}/api/chat/sessions/", headers={"Authorization": f"Bearer {jwt}"})
            data = r.json()
            results.append(("List chats", r.status_code, f"count={len(data)}"))
        except Exception as e:
            results.append(("List chats", 0, str(e)))

        # 13. Get settings
        try:
            r = await c.get(f"{base}/api/settings/", headers={"Authorization": f"Bearer {jwt}"})
            d = r.json()
            results.append(("Get settings", r.status_code, f"chunk={d.get('chunk_size')} llm={d.get('llm_provider')}"))
        except Exception as e:
            results.append(("Get settings", 0, str(e)))

        # 14. Update settings
        try:
            r = await c.put(f"{base}/api/settings/", json={
                "chunk_size": 256,
                "chunk_overlap": 32,
                "top_k": 10,
                "llm_provider": "openai",
                "llm_model": "gpt-4o-mini",
                "openai_api_base": "http://localhost:1234/v1"
            }, headers={"Authorization": f"Bearer {jwt}"})
            d = r.json()
            results.append(("Update settings", r.status_code, f"chunk={d.get('chunk_size')}"))
        except Exception as e:
            results.append(("Update settings", 0, str(e)))

        # 15. System stats
        try:
            r = await c.get(f"{base}/api/settings/stats", headers={"Authorization": f"Bearer {jwt}"})
            d = r.json()
            results.append(("Stats", r.status_code, f"docs={d.get('document_count')} chunks={d.get('chunk_count')} pg={d.get('postgres_connected')} neo4j={d.get('neo4j_connected')}"))
        except Exception as e:
            results.append(("Stats", 0, str(e)))

    # Print results
    print("=" * 80)
    print(f"{'Test':<20} {'Status':<8} {'Result':<50}")
    print("=" * 80)
    all_passed = True
    for name, status, result in results:
        status_str = "OK" if status == 200 or status == 201 else f"FAIL({status})"
        if status not in (200, 201):
            all_passed = False
        print(f"  {name:<18} {status_str:<8} {result}")
    print("=" * 80)
    print(f"\n{'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")

if __name__ == "__main__":
    # Start server in background thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    time.sleep(3)  # Wait for server to start

    # Run tests
    asyncio.run(test_api())

    sys.exit(0)
