"""Demo seed for CSC 3347 Machine Learning.

Runs only when OFFICEHOURS_DEMO is on. Accounts, notes, and rooms are
fictional. Course markdown is approved material. Classmate sketches stay
in the peer-note table and are not ingested into the Study Agent.
"""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.auth import Course, CourseMembership, User
from app.models.help_room import HelpPost, HelpReply
from app.models.knowledge import KnowledgeEntry
from app.models.peer_notes import PeerNote
from app.services.auth_service import hash_password
from app.services.demo_accounts import DEMO_PASSWORD
from app.services.demo_mode import demo_mode
from app.services.help_room_service import accept_reply, add_reply, create_post
from app.services.knowledge_service import ingest_course_material
from app.services.material_extract import extract_material_pages
from app.services.peer_notes_service import create_peer_note

COURSE_CODE = "CSC 3347"
COURSE_TITLE = "Machine Learning"
COURSE_TERM = "Spring 2026"
CLASSMATE_LABEL = "Shared by classmates, not checked by your professor"
DEMO_MARK = "demo"
# One token lives only in a classmate sketch, so a search can prove the
# Study Agent does not read peer notes. The other lives only in approved notes.
PEER_ONLY_TOKEN = "violetscratchtoken"
COURSE_ONLY_TOKEN = "cedarellipsecovariance"

_DATA = Path(__file__).resolve().parents[2] / "demo_data" / "ml"

_PEOPLE = (
    {
        "email": "r.tazi@aui.ma",
        "display_name": "Prof. Rim Tazi (demo)",
        "student_id": None,
        "handle": "r.tazi",
        "role": "professor",
        "bio": "Demo account. Fictional professor for the Machine Learning seed.",
    },
    {
        "email": "o.senhaji@aui.ma",
        "display_name": "Omar Senhaji (demo)",
        "student_id": "220340",
        "handle": "o.senhaji",
        "role": "ta",
        "bio": "Demo account. Fictional TA for the Machine Learning seed.",
    },
    {
        "email": "l.chraibi@aui.ma",
        "display_name": "Lina Chraibi (demo)",
        "student_id": "220341",
        "handle": "l.chraibi",
        "role": "student",
        "bio": "Demo account. Fictional student in CSC 3347.",
    },
    {
        "email": "a.fikri@aui.ma",
        "display_name": "Adam Fikri (demo)",
        "student_id": "220342",
        "handle": "a.fikri",
        "role": "student",
        "bio": "Demo account. Fictional student in CSC 3347.",
    },
    {
        "email": "s.bennani@aui.ma",
        "display_name": "Sofia Bennani (demo)",
        "student_id": "220343",
        "handle": "s.bennani",
        "role": "student",
        "bio": "Demo account. Fictional student in CSC 3347.",
    },
    {
        "email": "k.ouazzani@aui.ma",
        "display_name": "Karim Ouazzani (demo)",
        "student_id": "220344",
        "handle": "k.ouazzani",
        "role": "student",
        "bio": "Demo account. Fictional student in CSC 3347.",
    },
)

_COURSE_FILES = (
    "parametric_methods.md",
    "multivariate_gaussians.md",
    "mahalanobis_and_outliers.md",
)

_CLASSMATE_NOTES = (
    {
        "email": "l.chraibi@aui.ma",
        "filename": "classmate_parametric_sketch.md",
        "title": "Parametric sketch",
        "about": "Demo. Classmate sketch of parametric methods and a fixed theta.",
    },
    {
        "email": "a.fikri@aui.ma",
        "filename": "classmate_gaussian_mean.md",
        "title": "Mean vector sketch",
        "about": "Demo. Classmate sketch of the Gaussian mean vector.",
    },
    {
        "email": "s.bennani@aui.ma",
        "filename": "classmate_outlier_scratch.md",
        "title": "Outlier scratch",
        "about": "Demo. Classmate scratch about a point that looks extreme.",
    },
)


def _rooms() -> list[dict]:
    return [
        {
            "email": "l.chraibi@aui.ma",
            "title": "Parametric model: what stays fixed?",
            "chapter": "Parametric methods",
            "body": (
                "I can name the parameter vector, but I am not sure which part "
                "is chosen once and which part is the data. Is the length of "
                "theta fixed before we see the buoy sample?"
            ),
            "replies": [],
        },
        {
            "email": "a.fikri@aui.ma",
            "title": "Covariance matrix has to be symmetric?",
            "chapter": "Multivariate Gaussians",
            "body": (
                "When I write Sigma by hand, the off-diagonals disagree. Does "
                "the multivariate Gaussian require Sigma to equal its transpose, "
                "and what breaks if it does not?"
            ),
            "replies": [],
        },
        {
            "email": "s.bennani@aui.ma",
            "title": "Where do I cut an outlier?",
            "chapter": "Outliers",
            "body": (
                "A buoy sits far from the mean in height and close in wind. I "
                "do not know if a large Mahalanobis distance is enough to call "
                "it an outlier, or if I still need a cutoff chosen in advance."
            ),
            "replies": [],
        },
        {
            "email": "k.ouazzani@aui.ma",
            "title": "Mahalanobis versus plain Euclidean",
            "chapter": "Mahalanobis distance",
            "body": (
                "Euclidean distance treats every axis the same. The notes stretch "
                "the axes by the covariance. When is the Mahalanobis distance the "
                "one that matches the Gaussian, and when is Euclidean enough?"
            ),
            "replies": [
                {
                    "email": "s.bennani@aui.ma",
                    "body": (
                        "Use Mahalanobis when the cloud is tilted or stretched. "
                        "It is the Euclidean distance after you whiten by Sigma. "
                        "If Sigma is a multiple of the identity, the two rankings match."
                    ),
                }
            ],
        },
        {
            "email": "l.chraibi@aui.ma",
            "title": "Singular covariance, density will not compute",
            "chapter": "Multivariate Gaussians",
            "body": (
                "Every buoy reading lies on a line, so Sigma has determinant zero. "
                "The Gaussian density divides by the square root of that determinant. "
                "What should I do before I call it a density?"
            ),
            "replies": [
                {
                    "email": "a.fikri@aui.ma",
                    "body": (
                        "A singular Sigma means the cloud has no area in some "
                        "direction. Drop that direction, or add a small positive "
                        "number on the diagonal, before you invert Sigma."
                    ),
                }
            ],
        },
        {
            "email": "a.fikri@aui.ma",
            "title": "Mean vector is not one coordinate average",
            "chapter": "Multivariate Gaussians",
            "body": (
                "For one feature I would average the column. For two features, "
                "is mu just those column averages stacked, or does the covariance "
                "change the mean as well?"
            ),
            "replies": [
                {
                    "email": "k.ouazzani@aui.ma",
                    "body": (
                        "Mu is the vector of averages, one per feature. The "
                        "covariance does not move mu. It only describes how the "
                        "features vary together around that point."
                    ),
                }
            ],
        },
        {
            "email": "s.bennani@aui.ma",
            "title": "Sketching the ellipse of a 2D Gaussian",
            "chapter": "Multivariate Gaussians",
            "body": (
                "I can plot the sample mean. I want the ellipse from the notes. "
                "Which directions do the axes of that ellipse follow?"
            ),
            "replies": [
                {
                    "email": "l.chraibi@aui.ma",
                    "body": (
                        "The axes follow the eigenvectors of Sigma. Longer axes "
                        "go with larger eigenvalues. The center is mu, not the "
                        "origin, unless the mean is the zero vector."
                    ),
                }
            ],
        },
        {
            "email": "k.ouazzani@aui.ma",
            "title": "A point far from the mean but inside the cloud",
            "chapter": "Mahalanobis distance",
            "body": (
                "One buoy is many steps out on height and typical on wind. "
                "Euclidean distance says it is extreme. Does Mahalanobis agree "
                "if height and wind rise together?"
            ),
            "replies": [
                {
                    "email": "l.chraibi@aui.ma",
                    "body": (
                        "Whiten first. If height and wind move together, a shift "
                        "along that shared direction is cheaper than the same "
                        "shift across the thin side of the ellipse. Compare "
                        "(x-mu) transposed times Sigma inverse times (x-mu), "
                        "not the raw coordinates."
                    ),
                    "accept": True,
                }
            ],
        },
    ]


def seed_ml_demo(db: Session) -> None:
    """Create the fictional Machine Learning course. No-op unless demo mode is on."""
    if not demo_mode():
        return
    course = _ensure_course(db)
    users = _ensure_people(db, course)
    db.commit()
    _ensure_materials(db, course)
    _ensure_classmate_notes(db, course, users)
    _ensure_rooms(db, course, users)


def _ensure_course(db: Session) -> Course:
    course = (
        db.query(Course)
        .filter(Course.code == COURSE_CODE, Course.term == COURSE_TERM)
        .one_or_none()
    )
    if course is None:
        course = Course(
            code=COURSE_CODE,
            title=COURSE_TITLE,
            term=COURSE_TERM,
            canvas_course_id="3347",
            is_active=True,
        )
        db.add(course)
        db.flush()
    else:
        course.title = COURSE_TITLE
        course.canvas_course_id = course.canvas_course_id or "3347"
        course.is_active = True
        db.add(course)
    return course


def _ensure_people(db: Session, course: Course) -> dict[str, User]:
    found: dict[str, User] = {}
    for spec in _PEOPLE:
        user = db.query(User).filter(User.email == spec["email"]).one_or_none()
        if user is None:
            user = User(
                email=spec["email"],
                password_hash=hash_password(DEMO_PASSWORD),
                display_name=spec["display_name"],
                student_id=spec["student_id"],
                handle=spec["handle"],
                bio=spec["bio"],
                country="Morocco",
                is_active=True,
            )
            db.add(user)
            db.flush()
        else:
            user.display_name = spec["display_name"]
            user.student_id = spec["student_id"]
            user.handle = spec["handle"]
            user.bio = spec["bio"]
            user.is_active = True
            db.add(user)
        row = (
            db.query(CourseMembership)
            .filter(
                CourseMembership.course_id == course.id,
                CourseMembership.user_id == user.id,
            )
            .one_or_none()
        )
        if row is None:
            db.add(
                CourseMembership(
                    course_id=course.id,
                    user_id=user.id,
                    role=spec["role"],
                )
            )
        elif row.role != spec["role"]:
            row.role = spec["role"]
            db.add(row)
        found[spec["email"]] = user
    db.flush()
    return found


def _mark_material(entry: KnowledgeEntry) -> None:
    try:
        tags = json.loads(entry.tags or "[]")
    except json.JSONDecodeError:
        tags = []
    if not isinstance(tags, list):
        tags = []
    if DEMO_MARK not in tags:
        tags.append(DEMO_MARK)
    entry.tags = json.dumps([str(tag) for tag in tags])
    note = entry.professor_note or ""
    if DEMO_MARK not in note:
        entry.professor_note = f"{note} | {DEMO_MARK}".strip(" |")


def _ensure_materials(db: Session, course: Course) -> None:
    for filename in _COURSE_FILES:
        already = (
            db.query(KnowledgeEntry)
            .filter(
                KnowledgeEntry.course_id == course.id,
                KnowledgeEntry.source_filename == filename,
            )
            .first()
        )
        if already is not None:
            continue
        path = _DATA / filename
        data = path.read_bytes()
        pages, source = extract_material_pages(filename, data)
        title = path.stem.replace("_", " ")
        entries = ingest_course_material(
            db,
            title=title,
            content="\n\n".join(page.text for page in pages),
            source=source,
            course_id=course.id,
            course=course.code,
            auto_approve=True,
            filename=filename,
            pages=[(page.page_number, page.text) for page in pages],
        )
        for entry in entries:
            _mark_material(entry)
            db.add(entry)
        db.commit()


def _ensure_classmate_notes(db: Session, course: Course, users: dict[str, User]) -> None:
    for spec in _CLASSMATE_NOTES:
        already = (
            db.query(PeerNote)
            .filter(PeerNote.course_id == course.id, PeerNote.title == spec["title"])
            .first()
        )
        if already is not None:
            continue
        path = _DATA / spec["filename"]
        create_peer_note(
            db,
            course_id=course.id,
            author=users[spec["email"]],
            title=spec["title"],
            about=spec["about"],
            caption=CLASSMATE_LABEL,
            anonymous=False,
            filename=spec["filename"],
            content_type="text/markdown",
            data=path.read_bytes(),
        )


def _ensure_rooms(db: Session, course: Course, users: dict[str, User]) -> None:
    for spec in _rooms():
        post = (
            db.query(HelpPost)
            .filter(HelpPost.course_id == course.id, HelpPost.title == spec["title"])
            .one_or_none()
        )
        if post is None:
            post = create_post(
                db,
                course_id=course.id,
                author=users[spec["email"]],
                title=spec["title"],
                body=spec["body"],
                chapter=spec["chapter"],
                anonymous=False,
                room_type="problem",
                tags=[DEMO_MARK],
            )
        author = users[spec["email"]]
        for reply_spec in spec["replies"]:
            reply_author = users[reply_spec["email"]]
            existing = (
                db.query(HelpReply)
                .filter(
                    HelpReply.post_id == post.id,
                    HelpReply.author_user_id == reply_author.id,
                )
                .one_or_none()
            )
            if existing is None:
                existing = add_reply(
                    db,
                    post=post,
                    author=reply_author,
                    body=reply_spec["body"],
                    anonymous=False,
                )
            if reply_spec.get("accept") and post.status != "solved":
                accept_reply(db, reply=existing, post=post, user=author)
