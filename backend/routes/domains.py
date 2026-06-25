from fastapi import APIRouter, HTTPException

from backend.models.schemas import LibraryDomainCreate, LibraryDomainUpdate, PaperDomainAssignRequest
from backend.services.domain_service import (
    assign_paper_domain,
    create_library_domain,
    delete_library_domain,
    list_library_domains,
    seed_default_domains_if_needed,
    set_paper_domain,
    update_library_domain,
)

router = APIRouter(prefix="/api", tags=["domains"])


@router.get("/domains")
async def get_domains():
    await seed_default_domains_if_needed()
    return await list_library_domains()


@router.post("/domains")
async def create_domain(payload: LibraryDomainCreate):
    try:
        created = await create_library_domain(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return created


@router.patch("/domains/{domain_id}")
async def patch_domain(domain_id: str, payload: LibraryDomainUpdate):
    updated = await update_library_domain(domain_id, payload.model_dump())
    if not updated:
        raise HTTPException(status_code=404, detail="Domain not found")
    return updated


@router.delete("/domains/{domain_id}")
async def remove_domain(domain_id: str):
    try:
        deleted = await delete_library_domain(domain_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Domain not found")
    return deleted


@router.post("/papers/{paper_id}/domain")
async def set_domain(paper_id: str, payload: PaperDomainAssignRequest):
    ok = await set_paper_domain(paper_id, payload.domain_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Paper or domain not found")
    return {"paper_id": paper_id, "domain_id": payload.domain_id}
