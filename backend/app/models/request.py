"""
Pydantic / ORM models for a student request.

Placeholder fields to start from:

    class RequestCreate(BaseModel):
        text: str
        anonymous: bool = True
        student_id: str | None = None  # only if anonymous=False

    class RequestOut(RequestCreate):
        id: int
        category: str | None = None
        cluster_id: int | None = None
        recommended_action: str | None = None
"""
