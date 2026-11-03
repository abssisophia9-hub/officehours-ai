"""Build the submission PDF from the reviewed interim-report PDF.

The editable Word source was not present in the repository or upload bundle, so
this script makes the requested, auditable corrections directly on the rendered
PDF while preserving the university cover, conduct page, signature, footers,
Roman numerals, body pagination, tables, and figures that were not changed.
"""

from __future__ import annotations

from pathlib import Path

import cairosvg
import pymupdf


ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(
    "/home/ubuntu/.cursor/projects/agent-repos-officehours-ai/uploads/"
    "OfficeHours_AI_Capstone_Interim_Report_50ee.pdf"
)
OUTPUT = ROOT / "reports/midreport/OfficeHours_AI_Capstone_Interim_Report.pdf"
ARCH_PNG = ROOT / "docs/midreport/figures/architecture.png"
SCHEMA_SVG = ROOT / "docs/midreport/figures/database_schema.svg"
SCHEMA_PNG = ROOT / "reports/midreport/.database_schema.png"

TITLE = (
    "OfficeHours AI: A Professor-Stamped RAG and Multi-Channel Academic\n"
    "Support Network to Lower Student Help-Seeking Barriers and\n"
    "Streamline Repetitive Staff Work"
)


def redact(page: pymupdf.Page, rect: pymupdf.Rect) -> None:
    page.add_redact_annot(rect, fill=(1, 1, 1))
    page.apply_redactions()


def text_box(
    page: pymupdf.Page,
    rect: pymupdf.Rect,
    text: str,
    *,
    size: float = 10.5,
    font: str = "Times-Roman",
    align: int = pymupdf.TEXT_ALIGN_LEFT,
    lineheight: float = 1.18,
) -> None:
    spare = page.insert_textbox(
        rect,
        text,
        fontname=font,
        fontsize=size,
        lineheight=lineheight,
        align=align,
        color=(0, 0, 0),
    )
    if spare < 0:
        raise RuntimeError(f"text does not fit {rect}: {-spare:.1f} points short")


def replace_title(doc: pymupdf.Document) -> None:
    cover = doc[0]
    redact(cover, pymupdf.Rect(75, 305, 525, 355))
    text_box(
        cover,
        pymupdf.Rect(72, 304, 523, 364),
        TITLE,
        size=12.5,
        font="Times-Bold",
        align=pymupdf.TEXT_ALIGN_CENTER,
        lineheight=1.12,
    )

    statement = doc[2]
    redact(statement, pymupdf.Rect(58, 116, 538, 158))
    text_box(
        statement,
        pymupdf.Rect(58, 118, 538, 166),
        TITLE,
        size=10.4,
        align=pymupdf.TEXT_ALIGN_LEFT,
        lineheight=1.08,
    )


def add_jill_watson(doc: pymupdf.Document) -> None:
    page = doc[10]
    redact(page, pymupdf.Rect(56, 198, 538, 283))
    paragraph = (
        "Jill Watson shows an earlier course deployment in which a virtual teaching "
        "assistant answered routine questions and amplified instructor capacity "
        "(Goel & Polepeddi, 2016). Course-deployed assistants such as CodeHelp "
        "(Liffiton et al., 2023) and the CS50 duck (Liu et al., 2024) likewise show "
        "that guardrailed language-model help can operate at scale in programming "
        "courses. Kasneci et al. (2023) survey both the opportunities and the risk "
        "of unreliable answers. These systems motivate academic-support automation; "
        "OfficeHours AI differs by making professor approval, course isolation, "
        "citation, and refusal explicit gates."
    )
    text_box(page, pymupdf.Rect(58, 201, 534, 282), paragraph, size=10.2, lineheight=1.12)


def replace_agent_terminology(doc: pymupdf.Document) -> None:
    page = doc[4]
    redact(page, pymupdf.Rect(56, 457, 538, 541))
    paragraph = (
        "\"Agent\" names the inner model-driven component. The surrounding Study "
        "Agent remains a bounded workflow: an outer orchestration wrapper owns the "
        "execution loop, maximum iterations, timeouts, retries, state, session "
        "history and budgets. On each iteration the inner Agent Layer receives an "
        "immutable state snapshot and chooses only among call_tool, return_answer "
        "and halt. It cannot access the database, publish directly, manage retries "
        "or extend its own loop. This is limited agency inside deterministic "
        "controls, not an autonomous general-purpose agent."
    )
    text_box(page, pymupdf.Rect(58, 460, 534, 540), paragraph, size=10.0, lineheight=1.1)


def replace_architecture(doc: pymupdf.Document) -> None:
    page = doc[11]
    redact(page, pymupdf.Rect(55, 555, 540, 750))
    text_box(
        page,
        pymupdf.Rect(58, 560, 535, 579),
        "5.2 System architecture",
        size=11,
        font="Times-Bold",
    )
    prose = (
        "Architectural style. OfficeHours AI is a modular monolith, not a set of "
        "microservices. One FastAPI deployable contains cohesive route and service "
        "modules for Identity, Academic Support, Knowledge, and Study Agent "
        "orchestration. The React app dispatches directly to each module's routes, "
        "and every module receives its own SQLAlchemy session for direct reads and "
        "writes to the shared transactional database.\n\n"
        "This is the appropriate trade-off for one capstone team and one product: "
        "deployment, authentication, testing, and data consistency stay simple. "
        "Microservices would add remote-call failures, distributed transactions, "
        "service discovery, and operational overhead without a demonstrated need "
        "for independent scaling. The module boundaries keep later extraction "
        "possible if deployment or scaling evidence justifies it."
    )
    text_box(page, pymupdf.Rect(58, 583, 535, 748), prose, size=10.2, lineheight=1.12)

    figure = doc[12]
    redact(figure, pymupdf.Rect(52, 38, 542, 580))
    figure.insert_image(
        pymupdf.Rect(58, 44, 538, 348),
        filename=str(ARCH_PNG),
        keep_proportion=True,
    )
    text_box(
        figure,
        pymupdf.Rect(58, 354, 536, 386),
        "Figure 1: OfficeHours AI as a modular monolith. Solid green: the system "
        "boundary. Dashed orange: external resources. Every arrow names the trigger "
        "or data exchanged and the communication mechanism.",
        size=9.8,
        font="Times-Bold",
        lineheight=1.08,
    )
    prose = (
        "The React app calls Identity for authentication and session checks, "
        "Knowledge for upload and approval, and Academic Support for a persisted "
        "student chat turn. Each module reads and writes its own tables directly "
        "through an injected SQLAlchemy session; database traffic does not pass "
        "through the Study Agent.\n\n"
        "Academic Support invokes the outer orchestration wrapper for a Study Agent "
        "turn. The wrapper owns the execution loop, maximum iterations, timeouts, "
        "transport retries, state, session history and budget cuts. On each loop it "
        "passes an immutable state snapshot to the inner Agent Layer. That inner "
        "module performs one model-driven decision and returns call_tool, "
        "return_answer or halt; it owns no loop, retry counter or timeout."
    )
    text_box(figure, pymupdf.Rect(58, 398, 536, 565), prose, size=10.2, lineheight=1.12)


def replace_database_schema(doc: pymupdf.Document) -> None:
    page = doc[14]
    redact(page, pymupdf.Rect(54, 194, 541, 656))
    prose = (
        "The default database is SQLite at backend/officehours.db; DATABASE_URL can "
        "select Postgres. SQLAlchemy creates the schema at startup. The application "
        "currently defines 28 tables, while Figure 3 shows the seven core tables in "
        "the ER diagram and the matching DDL in docs/database_schema.sql.\n\n"
        "Only the three solid relationships are database constraints: "
        "course_memberships.user_id to users.id, course_memberships.course_id to "
        "courses.id, and auth_sessions.user_id to users.id. The dashed "
        "requests.course_id and knowledge_entries.course_id links are plain INTEGER "
        "columns. Unique constraints protect users.email, auth_sessions.token, "
        "ta_roster.name, and each (course_id, user_id) membership pair."
    )
    text_box(page, pymupdf.Rect(58, 198, 535, 316), prose, size=9.7, lineheight=1.1)
    cairosvg.svg2png(
        bytestring=SCHEMA_SVG.read_bytes(),
        write_to=str(SCHEMA_PNG),
        output_width=2000,
        output_height=1120,
    )
    page.insert_image(pymupdf.Rect(58, 322, 536, 590), filename=str(SCHEMA_PNG))
    text_box(
        page,
        pymupdf.Rect(58, 600, 536, 636),
        "Figure 3: Core SQL DDL schema. Solid lines are the only declared foreign "
        "keys; dashed lines are unconstrained INTEGER links. All identifiers use "
        "lowercase snake_case.",
        size=9.8,
        font="Times-Bold",
        lineheight=1.08,
    )


def correct_ai_disclosure(doc: pymupdf.Document) -> None:
    page = doc[17]
    redact(page, pymupdf.Rect(56, 454, 538, 540))
    paragraph = (
        "The retained history records substantial agent-generated implementation. "
        "I defined requirements, selected tasks, reviewed proposed changes, ran the "
        "tests and decided whether to merge each pull request. Author attribution "
        "cannot prove who designed every line, so Table 10 is an implementation "
        "audit rather than a measure of intellectual ownership. It would also be "
        "inaccurate to describe Cursor as only debugging code I had already written: "
        "the commit and line records show broader implementation assistance. This "
        "evidence-based disclosure supersedes Diary 1's narrower description."
    )
    text_box(page, pymupdf.Rect(58, 457, 534, 539), paragraph, size=10.0, lineheight=1.1)


def correct_agent_controls(doc: pymupdf.Document) -> None:
    page = doc[16]
    redact(page, pymupdf.Rect(62, 441, 525, 455))
    text_box(page, pymupdf.Rect(64, 443, 194, 454), "Agent call / outer retry", size=6.6)
    text_box(page, pymupdf.Rect(198, 443, 345, 454), "1 / 2", size=6.6)
    text_box(
        page,
        pymupdf.Rect(349, 443, 524, 454),
        "One model call per agent step; retry belongs to wrapper",
        size=6.4,
    )

    redact(page, pymupdf.Rect(56, 655, 538, 740))
    paragraph = (
        "In the product. When armed, the outer wrapper supplies approved chunks and "
        "the current state to the inner Agent Layer. One invocation makes one model "
        "decision: call a bounded tool, return an answer, or halt. The wrapper alone "
        "owns retries, timeouts, iteration limits, history and budgets. The saved "
        "Gemini run used gemini-3.5-flash-lite with prompt study-answer-check-v1 "
        "before this layered refactor, so its 74/75 result measures the saved "
        "quote-check configuration, not the newer recovery loop. No model was called "
        "while rebuilding this report."
    )
    text_box(page, pymupdf.Rect(58, 659, 534, 739), paragraph, size=9.8, lineheight=1.1)


REFERENCES = [
    "Abssi, S. (2026). OfficeHours AI: A multi-role campus office-hours triage system with custom-trained Ask Triage agents [Capstone project proposal, EGR 4402]. School of Science and Engineering, Al Akhawayn University.",
    "Anthropic. (2024). Building effective agents. https://www.anthropic.com/research/building-effective-agents",
    "Asai, A., Wu, Z., Wang, Y., Sil, A., & Hajishirzi, H. (2024). Self-RAG: Learning to retrieve, generate, and critique through self-reflection. The Twelfth International Conference on Learning Representations. https://arxiv.org/abs/2310.11511",
    "Goel, A. K., & Polepeddi, L. (2016). Jill Watson: A virtual teaching assistant for online education. Georgia Institute of Technology. https://repository.gatech.edu/entities/publication/4a7ab707-3311-4c67-a3c5-c309873d75f5",
    "Greshake, K., Abdelnabi, S., Mishra, S., Endres, C., Holz, T., & Fritz, M. (2023). Not what you've signed up for: Compromising real-world LLM-integrated applications with indirect prompt injection. Proceedings of the 16th ACM Workshop on Artificial Intelligence and Security. https://doi.org/10.1145/3605764.3623985",
    "Kasneci, E., Seßler, K., Küchemann, S., Bannert, M., Dementieva, D., Fischer, F., et al. (2023). ChatGPT for good? On opportunities and challenges of large language models for education. Learning and Individual Differences, 103, 102274. https://doi.org/10.1016/j.lindif.2023.102274",
    "Kingdom of Morocco. (2009). Law No. 09-08 on the protection of individuals with regard to the processing of personal data. Commission Nationale de contrôle de la protection des Données à caractère Personnel. https://www.cndp.ma",
    "Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., et al. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. Advances in Neural Information Processing Systems, 33, 9459–9474.",
    "Liffiton, M., Sheese, B. E., Šavelka, J., & Denny, P. (2023). CodeHelp: Using large language models with guardrails for scalable support in programming classes. Proceedings of the 23rd Koli Calling International Conference on Computing Education Research. https://doi.org/10.1145/3631802.3631830",
    "Liu, R., Zenke, C., Liu, C., Holmes, A., Thornton, P., & Malan, D. J. (2024). Teaching CS50 with AI: Leveraging generative artificial intelligence in computer science education. Proceedings of the 55th ACM Technical Symposium on Computer Science Education V. 1, 750–756. https://doi.org/10.1145/3626252.3630938",
    "OWASP Foundation. (n.d.). OWASP top 10 for large language model applications. https://genai.owasp.org/llm-top-10/",
    "Perez, F., & Ribeiro, I. (2022). Ignore previous prompt: Attack techniques for language models. arXiv. https://arxiv.org/abs/2211.09527",
    "Rashkin, H., Nikolaev, V., Lamm, M., Aroyo, L., Collins, M., Das, D., et al. (2023). Measuring attribution in natural language generation models. Computational Linguistics, 49(4), 777–840. https://doi.org/10.1162/coli_a_00486",
    "Reimers, N., & Gurevych, I. (2019). Sentence-BERT: Sentence embeddings using Siamese BERT-networks. Proceedings of EMNLP-IJCNLP, 3982–3992. https://doi.org/10.18653/v1/D19-1410",
    "Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference. Journal of the American Statistical Association, 22(158), 209–212. https://doi.org/10.1080/01621459.1927.10502953",
    "Yan, S.-Q., Gu, J.-C., Zhu, Y., & Ling, Z.-H. (2024). Corrective retrieval augmented generation. arXiv. https://arxiv.org/abs/2401.15884",
]


def replace_references(doc: pymupdf.Document) -> None:
    first, second = doc[22], doc[23]
    redact(first, pymupdf.Rect(54, 62, 541, 760))
    redact(second, pymupdf.Rect(54, 62, 541, 755))
    text_box(first, pymupdf.Rect(58, 66, 536, 88), "7 References", size=12, font="Times-Bold")

    # A fixed split keeps both pages balanced and preserves body page numbers 19–20.
    groups = [(first, REFERENCES[:10], 94), (second, REFERENCES[10:], 67)]
    for page, refs, top in groups:
        y = top
        for reference in refs:
            height = 67 if len(reference) > 310 else 56 if len(reference) > 220 else 45
            text_box(
                page,
                pymupdf.Rect(58, y, 536, y + height),
                reference,
                size=9.2,
                lineheight=1.08,
            )
            y += height
        if y > 758:
            raise RuntimeError(f"references overflow page {page.number + 1}: {y}")


def add_metadata(doc: pymupdf.Document) -> None:
    metadata = doc.metadata
    metadata.update(
        {
            "title": TITLE.replace("\n", " "),
            "author": "Sophia Abssi",
            "subject": "Capstone Design Interim Report",
            "keywords": "OfficeHours AI, RAG, modular monolith, academic support",
        }
    )
    doc.set_metadata(metadata)


def main() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(SOURCE)
    replace_title(doc)
    replace_agent_terminology(doc)
    add_jill_watson(doc)
    replace_architecture(doc)
    replace_database_schema(doc)
    correct_ai_disclosure(doc)
    correct_agent_controls(doc)
    replace_references(doc)
    add_metadata(doc)
    doc.save(OUTPUT, garbage=4, deflate=True, clean=True)
    doc.close()
    SCHEMA_PNG.unlink(missing_ok=True)
    print(OUTPUT)


if __name__ == "__main__":
    main()
