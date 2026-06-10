"""
MCP Server Integration Test — Mock Company Data

Tests the MCP server with realistic company data:
- 2 tenants (companies) to verify tenant isolation
- Multiple departments per tenant
- Documents scoped to departments
- RAG queries to verify access control

Run with:
  cd /home/yo/Desktop/code/proairag && docker compose up -d
  python tests/test_mcp_server.py
  docker compose down
"""

import asyncio
import hashlib
import json
import math
import sys
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Setup DB connection
from src.db.session import async_session


def _tid(name: str) -> str:
    """Deterministic UUID from name for reproducibility."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"mcp-test-{name}"))


def _hash_embed(text: str) -> str:
    """Hash-based embedding fallback."""
    dim = 384
    hash_bytes = hashlib.sha256(text.encode()).digest()
    values = [int(b) / 255.0 for b in hash_bytes * (dim // 32 + 1)]
    norm = math.sqrt(sum(v * v for v in values[:dim])) or 1.0
    vec = [v / norm for v in values[:dim]]
    return "[" + ",".join(str(x) for x in vec) + "]"


# ─── Company 1: AeroTech Solutions ─────────────────────────────────────────

AEROTECH = {
    "name": "AeroTech Solutions",
    "api_key": "sk-aerotech-test-key",
    "departments": {
        "engineering": "Engineering & R&D",
        "security": "Cybersecurity & Compliance",
        "hr": "Human Resources",
    },
    "users": {
        "alice": {"email": "alice.chen@aerotech.com", "password": "pass123", "name": "Alice Chen", "admin": True},
        "bob": {"email": "bob.martinez@aerotech.com", "password": "pass123", "name": "Bob Martinez", "admin": False},
        "carol": {"email": "carol.johnson@aerotech.com", "password": "pass123", "name": "Carol Johnson", "admin": False},
    },
}

# ─── Company 2: DataVault Inc ──────────────────────────────────────────────

DATAVAULT = {
    "name": "DataVault Inc",
    "api_key": "sk-datavault-test-key",
    "departments": {
        "analytics": "Data Analytics",
        "legal": "Legal & Compliance",
    },
    "users": {
        "dave": {"email": "dave.wilson@datavault.com", "password": "pass123", "name": "Dave Wilson", "admin": True},
        "eve": {"email": "eve.garcia@datavault.com", "password": "pass123", "name": "Eve Garcia", "admin": False},
    },
}

# ─── Documents scoped to departments ───────────────────────────────────────

DOCUMENTS = {
    # AeroTech - Engineering docs
    "aerotech-engineering-1": {
        "tenant": AEROTECH,
        "department": "engineering",
        "title": "Jet Engine Turbine Specs",
        "content": (
            "The AeroTech X-500 jet engine turbine operates at 4500°C with a thermal "
            "efficiency of 42%. The nickel-based superalloy blades use single-crystal "
            "casting with rhenium content of 6% for creep resistance. Maximum thrust is "
            "160 kN at sea level. Fuel consumption is 0.58 lb/lbf-hr. The turbine "
            "design incorporates active film cooling channels with 0.5mm diameter holes "
            "arranged in 4 rows. Material cost per blade is $12,000. Certification "
            "requires FAA Type Certificate under Part 33."
        ),
    },
    "aerotech-engineering-2": {
        "tenant": AEROTECH,
        "department": "engineering",
        "title": "Composites Manufacturing Process",
        "content": (
            "AeroTech uses carbon fiber reinforced polymer (CFRP) for wing structures. "
            "The autoclave curing cycle requires 180°C for 3 hours at 6 bar pressure. "
            "Prepreg material T800H-12K-240G from Toray is specified. Layup follows "
            "quasi-isotropic [0/90/+45/-45]s orientation. Quality control requires "
            "ultrasonic C-scanning at 100% coverage. First article inspection cost is "
            "$45,000 per wing section. Supplier: Toray Industries, contract #AT-2025-0412."
        ),
    },
    # AeroTech - Security docs
    "aerotech-security-1": {
        "tenant": AEROTECH,
        "department": "security",
        "title": "Network Security Architecture v3.2",
        "content": (
            "AeroTech network security uses zero-trust architecture with micro-segmentation. "
            "All internal services require mutual TLS (mTLS) authentication. The SOC "
            "operates 24/7 with SIEM correlation rules for threat detection. "
            "Vulnerability scanning runs daily on external-facing systems. Penetration "
            "testing budget is $250,000 annually. Incident response SLA: 15 minutes for "
            "critical, 2 hours for high severity. Contact: SOC at soc@aerotech.com, "
            "emergency hotline +1-555-0199."
        ),
    },
    "aerotech-security-2": {
        "tenant": AEROTECH,
        "department": "security",
        "title": "Incident Response Plan",
        "content": (
            "In case of security incident, immediately contact the SOC. Step 1: Isolate "
            "affected systems from network. Step 2: Preserve forensic evidence. Step 3: "
            "Notify CISO within 1 hour. Step 4: Begin root cause analysis. Data breach "
            "notification required within 72 hours under GDPR. Insurance policy #SEC-2025-8847 "
            "covers up to $10M in breach costs. External IR team: CrowdStrike, contact "
            "aerotech@crowdstrike.com."
        ),
    },
    # AeroTech - HR docs
    "aerotech-hr-1": {
        "tenant": AEROTECH,
        "department": "hr",
        "title": "Employee Benefits Handbook 2025",
        "content": (
            "AeroTech employees receive comprehensive health insurance with $200 annual "
            "deductible. 401(k) matching up to 6% of salary. Annual leave: 20 days base "
            "plus 1 day per year of service. Remote work policy: 3 days per week allowed "
            "after 90-day probation. Performance bonus: 5-15% based on annual review. "
            "Parental leave: 12 weeks paid. Tuition reimbursement up to $5,000 per year. "
            "Contact HR at hr@aerotech.com or phone +1-555-0150."
        ),
    },
    # DataVault - Analytics docs
    "datavault-analytics-1": {
        "tenant": DATAVAULT,
        "department": "analytics",
        "title": "Q4 Revenue Forecast Model",
        "content": (
            "DataVault Q4 2025 revenue forecast: $42.3M projected, representing 18% "
            "YoY growth. Primary drivers: enterprise subscriptions (62% of revenue), "
            "API usage fees (25%), professional services (13%). Customer acquisition cost "
            "is $2,400 per enterprise client. Churn rate: 3.2% monthly. LTV:CAC ratio "
            "is 8.5. The model uses ARIMA time series with seasonal decomposition. "
            "Confidence interval: 95% [38.5M to 46.1M]. Next review: January 15, 2026."
        ),
    },
    "datavault-analytics-2": {
        "tenant": DATAVAULT,
        "department": "analytics",
        "title": "Customer Segmentation Analysis",
        "content": (
            "DataVault customer segments: Enterprise (340 clients, avg. 95K per year), "
            "Mid-market (1,200 clients, avg. 18K per year), Startup (3,500 clients, avg. 3K per year). "
            "Enterprise customers use 78% of API calls. Geographic distribution: US (45%), "
            "EU (30%), APAC (20%), Other (5%). Top industries: Financial Services (28%), "
            "Healthcare (22%), E-commerce (18%), Manufacturing (15%). Cohort analysis shows "
            "retention rate of 89% after 12 months for Enterprise tier."
        ),
    },
    # DataVault - Legal docs
    "datavault-legal-1": {
        "tenant": DATAVAULT,
        "department": "legal",
        "title": "Data Processing Agreement Template",
        "content": (
            "DataVault DPA complies with GDPR, CCPA, and SOC 2 Type II. Data subjects: "
            "end-users of DataVault platform. Processing purposes: analytics, reporting, "
            "ML model training. Data retention: 24 months after contract termination. "
            "Cross-border transfer mechanism: EU Standard Contractual Clauses 2021. "
            "Sub-processors: AWS (US), Snowflake (US), Datadog (US/France). "
            "Data Protection Officer: dpo@datavault.com. Breach notification: within "
            "24 hours to supervisory authority."
        ),
    },
}

# ─── Department assignments (user -> departments) ──────────────────────────

USER_DEPTS = {
    "bob": ["engineering"],       # Bob sees Engineering only
    "carol": ["security", "hr"],  # Carol sees Security AND HR
    "eve": ["analytics"],         # Eve sees Analytics only
}


async def setup_data():
    """Create tenants, departments, users, and documents via raw SQL."""
    results = {}

    async with async_session() as db:
        # ── Create tenants ──
        for comp_name, comp in [("AeroTech", AEROTECH), ("DataVault", DATAVAULT)]:
            tid = _tid(comp_name)
            await db.execute(
                text("""INSERT INTO tenants (id, name, api_key, is_active)
                        VALUES (:id, :name, :api_key, true)
                        ON CONFLICT (id) DO NOTHING"""),
                {"id": tid, "name": comp["name"], "api_key": comp["api_key"]},
            )
            results[comp_name] = {"tenant_id": tid, "departments": {}, "users": {}}

            # ── Create departments ──
            for dept_key, dept_name in comp["departments"].items():
                did = _tid(f"{comp_name}-{dept_key}")
                await db.execute(
                    text("""INSERT INTO departments (id, tenant_id, name, description)
                            VALUES (:id, :tenant_id, :name, :desc)
                            ON CONFLICT (id) DO NOTHING"""),
                    {"id": did, "tenant_id": tid, "name": dept_name, "desc": f"{comp_name} - {dept_name}"},
                )
                results[comp_name]["departments"][dept_key] = did

            # ── Create users ──
            from passlib.context import CryptContext

            pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
            for user_key, user in comp["users"].items():
                uid = _tid(f"{comp_name}-{user_key}")
                pw_hash = pwd_ctx.hash(user["password"])
                await db.execute(
                    text("""INSERT INTO users (id, tenant_id, email, password_hash,
                            full_name, is_tenant_admin, is_active)
                            VALUES (:id, :tenant_id, :email, :pw_hash, :full_name,
                            :is_admin, true)
                            ON CONFLICT (id) DO NOTHING"""),
                    {
                        "id": uid,
                        "tenant_id": tid,
                        "email": user["email"],
                        "pw_hash": pw_hash,
                        "full_name": user["name"],
                        "is_admin": user["admin"],
                    },
                )
                results[comp_name]["users"][user_key] = uid

        await db.commit()

        # ── Assign users to departments ──
        # Map user keys to (results_key, user_id)
        user_to_results: dict[str, tuple[str, str]] = {}
        for comp_name in ["AeroTech", "DataVault"]:
            for user_key, uid in results[comp_name]["users"].items():
                user_to_results[user_key] = (comp_name, uid)

        for user_key, dept_keys in USER_DEPTS.items():
            if user_key not in user_to_results:
                continue
            comp_name, uid = user_to_results[user_key]

            for dept_key in dept_keys:
                did = results[comp_name]["departments"][dept_key]
                await db.execute(
                    text("""INSERT INTO user_departments (user_id, department_id, role)
                            VALUES (:user_id, :dept_id, 'member')
                            ON CONFLICT (user_id, department_id) DO NOTHING"""),
                    {"user_id": uid, "dept_id": did},
                )

        await db.commit()

        # ── Ingest documents ──
        # Map company objects to results keys
        comp_to_key = {"AeroTech Solutions": "AeroTech", "DataVault Inc": "DataVault"}

        for doc_key, doc in DOCUMENTS.items():
            comp = doc["tenant"]
            rk = comp_to_key[comp["name"]]
            tid = results[rk]["tenant_id"]
            dept_id = results[rk]["departments"][doc["department"]]
            doc_id = _tid(f"doc-{doc_key}")

            # Chunk text
            words = doc["content"].split()
            chunks_text: list[str] = []
            for i in range(0, len(words), 512 - 64):
                chunk_words = words[i : i + 512]
                if chunk_words:
                    chunks_text.append(" ".join(chunk_words))
            if not chunks_text:
                chunks_text = [doc["content"]]

            embeddings_str = [_hash_embed(ct) for ct in chunks_text]

            # Insert document
            await db.execute(
                text("""INSERT INTO documents (id, tenant_id, department_id, title,
                        content, source, content_type, is_processed)
                        VALUES (:id, :tid, :dept_id, :title, :content, :source, :ct, true)
                        ON CONFLICT (id) DO NOTHING"""),
                {
                    "id": doc_id,
                    "tid": tid,
                    "dept_id": dept_id,
                    "title": doc["title"],
                    "content": doc["content"],
                    "source": "mcp-test",
                    "ct": "text",
                },
            )

            # Insert chunks
            for i, (ct, emb) in enumerate(zip(chunks_text, embeddings_str)):
                chunk_id = _tid(f"chunk-{doc_key}-{i}")
                await db.execute(
                    text("""INSERT INTO chunks (id, tenant_id, document_id, content,
                            embedding, chunk_index)
                            VALUES (:id, :tid, :doc_id, :content,
                            CAST(:emb AS vector), :idx)
                            ON CONFLICT (id) DO NOTHING"""),
                    {
                        "id": chunk_id,
                        "tid": tid,
                        "doc_id": doc_id,
                        "content": ct,
                        "emb": emb,
                        "idx": i,
                    },
                )

        await db.commit()

    return results


async def verify_data(results: dict):
    """Verify the setup data is correct."""
    print("\n" + "=" * 70)
    print("  DATA SETUP VERIFICATION")
    print("=" * 70)

    async with async_session() as db:
        counts = ["tenants", "departments", "users", "user_departments", "documents", "chunks"]
        for table in counts:
            r = await db.execute(text(f"SELECT COUNT(*) FROM {table}"))
            print(f"\n  {table}: {r.scalar()}")

        # Show tenant details
        r = await db.execute(text("SELECT id, name, is_active FROM tenants ORDER BY name"))
        print("\n  Tenants:")
        for row in r.mappings().all():
            print(f"    - {row['name']} (id={str(row['id'])[:8]}..., active={row['is_active']})")

        # Show department per tenant
        r = await db.execute(
            text("""SELECT d.name, t.name as tenant FROM departments d
                    JOIN tenants t ON d.tenant_id = t.id ORDER BY t.name, d.name""")
        )
        print("\n  Departments per tenant:")
        for row in r.mappings().all():
            print(f"    [{row['tenant']}] {row['name']}")

        # Show user-department assignments
        r = await db.execute(
            text("""SELECT u.full_name, u.email, d.name as department, t.name as tenant
                    FROM user_departments ud
                    JOIN users u ON ud.user_id = u.id
                    JOIN departments d ON ud.department_id = d.id
                    JOIN tenants t ON u.tenant_id = t.id
                    ORDER BY t.name, u.full_name, d.name""")
        )
        print("\n  User access (who sees which departments):")
        for row in r.mappings().all():
            print(f"    [{row['tenant']}] {row['full_name']} ({row['email']}) -> {row['department']}")

        # Show documents
        r = await db.execute(
            text("""SELECT d.title, d.content_type, dp.name as department, t.name as tenant
                    FROM documents d
                    JOIN departments dp ON d.department_id = dp.id
                    JOIN tenants t ON d.tenant_id = t.id
                    ORDER BY t.name, dp.name, d.title""")
        )
        print("\n  Documents per department:")
        for row in r.mappings().all():
            print(f"    [{row['tenant']} / {row['department']}] {row['title']}")

    print("\n  Setup complete! All mock data inserted.")

    # Print IDs for MCP testing
    print(f"\n  Tenant IDs for MCP testing:")
    print(f"    AeroTech:  {results['AeroTech']['tenant_id']}")
    print(f"    DataVault: {results['DataVault']['tenant_id']}")

    for comp_name in ["AeroTech", "DataVault"]:
        print(f"\n  {comp_name} departments:")
        for dept_key, dept_id in results[comp_name]["departments"].items():
            print(f"    {dept_key}: {dept_id}")

        print(f"\n  {comp_name} users:")
        for user_key, user_id in results[comp_name]["users"].items():
            admin = " (admin)" if user_key in ["alice", "dave"] else ""
            depts = USER_DEPTS.get(user_key, ["ALL (admin)"])
            print(f"    {user_key}: {user_id} {admin} [depts: {', '.join(depts)}]")

    return results


async def main():
    print("=" * 70)
    print("  MCP Server Test — Mock Company Data Setup")
    print("=" * 70)
    print("  Companies: AeroTech Solutions + DataVault Inc")
    print("  Departments: Engineering, Security, HR, Analytics, Legal")
    print("  Documents: 7 documents across departments")
    print()

    results = await setup_data()
    await verify_data(results)

    print("\n" + "=" * 70)
    print("  NEXT: Test MCP tools with this data")
    print("=" * 70)

    at = results["AeroTech"]["tenant_id"]
    dv = results["DataVault"]["tenant_id"]

    print(f"""
  Run these MCP tests:

  # 1. List tenants (should show 2+)
  fastmcp call src/mcp_server.py list_tenants

  # 2. AeroTech departments
  fastmcp call src/mcp_server.py list_departments tenant_id="{at}"

  # 3. AeroTech documents (all dept docs visible)
  fastmcp call src/mcp_server.py list_documents tenant_id="{at}"

  # 4. RAG: Query AeroTech engineering doc
  fastmcp call src/mcp_server.py rag_query \\
    query="What is the turbine efficiency?" \\
    tenant_id="{at}"

  # 5. RAG: Query DataVault analytics doc
  fastmcp call src/mcp_server.py rag_query \\
    query="What is the Q4 revenue forecast?" \\
    tenant_id="{dv}"

  # 6. TENANT ISOLATION: AeroTech should NOT see DataVault docs
  fastmcp call src/mcp_server.py rag_query \\
    query="What is the Q4 revenue forecast?" \\
    tenant_id="{at}"

  # 7. DataVault departments (different from AeroTech)
  fastmcp call src/mcp_server.py list_departments tenant_id="{dv}"

  # 8. RAG: Security incident response
  fastmcp call src/mcp_server.py rag_query \\
    query="How to handle a security incident?" \\
    tenant_id="{at}"

  # 9. RAG: Employee benefits query
  fastmcp call src/mcp_server.py rag_query \\
    query="What is the annual leave policy?" \\
    tenant_id="{at}"

  # 10. RAG: Cross-tenant isolation (DataVault should NOT see AeroTech)
  fastmcp call src/mcp_server.py rag_query \\
    query="What is the turbine efficiency?" \\
    tenant_id="{dv}"
""")


if __name__ == "__main__":
    asyncio.run(main())
