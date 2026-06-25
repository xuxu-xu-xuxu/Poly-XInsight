from __future__ import annotations

from sqlalchemy import case, delete, func, select

from backend.models.database import DEFAULT_LIBRARY_DOMAINS, LibraryDomain, Paper, PaperDomainAssignment, get_db


async def list_library_domains() -> list[dict]:
    async for db in get_db():
        result = await db.execute(
            select(
                LibraryDomain.id,
                LibraryDomain.name,
                LibraryDomain.description,
                LibraryDomain.color,
                LibraryDomain.sort_order,
                LibraryDomain.is_default,
                func.count(PaperDomainAssignment.paper_id).label("paper_count"),
                func.coalesce(func.sum(case((Paper.status == "ingested", 1), else_=0)), 0).label("ingested_count"),
                func.coalesce(func.sum(case((Paper.status == "processing", 1), else_=0)), 0).label("processing_count"),
                func.coalesce(func.sum(case((Paper.status == "failed", 1), else_=0)), 0).label("failed_count"),
                func.max(Paper.created_at).label("latest_paper_at"),
            )
            .select_from(LibraryDomain)
            .outerjoin(PaperDomainAssignment, PaperDomainAssignment.domain_id == LibraryDomain.id)
            .outerjoin(Paper, Paper.id == PaperDomainAssignment.paper_id)
            .group_by(
                LibraryDomain.id,
                LibraryDomain.name,
                LibraryDomain.description,
                LibraryDomain.color,
                LibraryDomain.sort_order,
                LibraryDomain.is_default,
            )
            .order_by(LibraryDomain.sort_order.asc(), LibraryDomain.name.asc())
        )
        rows = result.fetchall()
        break

    return [
        {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "color": row[3],
            "sort_order": row[4],
            "is_default": row[5],
            "paper_count": int(row[6] or 0),
            "ingested_count": int(row[7] or 0),
            "processing_count": int(row[8] or 0),
            "failed_count": int(row[9] or 0),
            "latest_paper_at": row[10],
        }
        for row in rows
    ]


async def create_library_domain(payload) -> dict:
    async for db in get_db():
        existing_id = await db.get(LibraryDomain, payload["id"])
        if existing_id:
            raise ValueError("Domain already exists")
        existing_name = await db.scalar(select(LibraryDomain).where(LibraryDomain.name == payload["name"]))
        if existing_name:
            raise ValueError("Domain name already exists")
        domain = LibraryDomain(**payload)
        db.add(domain)
        await db.commit()
        return {
            "id": domain.id,
            "name": domain.name,
            "description": domain.description,
            "color": domain.color,
            "sort_order": domain.sort_order,
            "is_default": domain.is_default,
        }


async def update_library_domain(domain_id: str, payload) -> dict:
    async for db in get_db():
        domain = await db.get(LibraryDomain, domain_id)
        if not domain:
            return {}
        for key, value in payload.items():
            if value is not None:
                setattr(domain, key, value)
        await db.commit()
        return {
            "id": domain.id,
            "name": domain.name,
            "description": domain.description,
            "color": domain.color,
            "sort_order": domain.sort_order,
            "is_default": domain.is_default,
        }


async def delete_library_domain(domain_id: str) -> dict:
    async for db in get_db():
        domain = await db.get(LibraryDomain, domain_id)
        if not domain:
            return {}
        if domain.is_default:
            raise ValueError("Default domains cannot be deleted")
        fallback = await db.get(LibraryDomain, "unclassified")
        if not fallback:
            raise ValueError("Fallback domain not found")
        assignments = (
            await db.execute(
                select(PaperDomainAssignment).where(PaperDomainAssignment.domain_id == domain_id)
            )
        ).scalars().all()
        for assignment in assignments:
            assignment.domain_id = fallback.id
        reassigned_count = len(assignments)
        await db.delete(domain)
        await db.commit()
        return {"deleted": domain_id, "reassigned_to": fallback.id, "paper_count": reassigned_count}


async def assign_paper_domain(db, paper_id: str, domain_id: str) -> None:
    await db.execute(delete(PaperDomainAssignment).where(PaperDomainAssignment.paper_id == paper_id))
    db.add(PaperDomainAssignment(paper_id=paper_id, domain_id=domain_id))


async def set_paper_domain(paper_id: str, domain_id: str) -> bool:
    async for db in get_db():
        paper = await db.get(Paper, paper_id)
        domain = await db.get(LibraryDomain, domain_id)
        if not paper or not domain:
            return False
        await assign_paper_domain(db, paper_id, domain_id)
        await db.commit()
        return True


async def seed_default_domains_if_needed() -> None:
    async for db in get_db():
        result = await db.execute(select(func.count()).select_from(LibraryDomain))
        count = result.scalar_one()
        if count == 0:
            for payload in DEFAULT_LIBRARY_DOMAINS:
                db.add(LibraryDomain(**payload))
            await db.commit()
        break
