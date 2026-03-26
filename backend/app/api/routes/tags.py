from fastapi import APIRouter, Depends

from app.api.auth import require_auth
from app.api.deps import get_tag_repository
from app.repositories.relational import PostgresTagRepository
from app.schemas.tag import TagResponse

router = APIRouter(prefix="/api/v1/tags", tags=["tags"])


@router.get("", response_model=list[TagResponse])
async def list_tags(
    _user=Depends(require_auth),
    tag_repo: PostgresTagRepository = Depends(get_tag_repository),
):
    tags_with_counts = await tag_repo.get_with_counts()
    return [
        TagResponse(id=tag.id, name=tag.name, category=tag.category, memory_count=count)
        for tag, count in tags_with_counts
    ]
