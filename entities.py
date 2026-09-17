from pydantic import BaseModel, Field


class Cell(BaseModel):
    """
    One worksheet cell, identified by index.
    """

    id: int = Field(
        description="The [N] index shown before this cell in the input, copied exactly"
    )
    topic: str = Field(
        description="Short theme label for this cell, 2-4 words, in the source language"
    )
    is_a_question: bool = Field(
        description=(
            "True if the cell is a question or a filling instruction addressed to the "
            "candidate -- imperative mood or second person, e.g. 'Перераховуйте все...', "
            "'Дайте волю...'. False if it is the candidate's own answer -- first person, "
            "concrete, e.g. 'Люблю будувати...', 'Розробив...'. Position is not a "
            "reliable signal: some columns open with an instruction, others with an answer."
        )
    )


class Questions(BaseModel):
    column: list[Cell] = Field(description="Column containing questions")


class Answers(BaseModel):
    column: list[Cell] = Field(description="Column containing answers")


class WorkExperience(BaseModel):
    company: str
    position: str = Field(description="Job title held")
    start_date: str = Field(description="ISO format YYYY-MM")
    end_date: str | None = Field(default=None, description="None if current")
    highlights: list[str] = Field(
        description="Concrete achievements with measurable outcomes, not duties"
    )
    skills: list[str] = Field(description="Technologies and tools used in this role")


class Education(BaseModel):
    institution: str
    area: str = Field(description="Field of study")
    study_type: str = Field(description="Bachelor, Master, course, etc.")
    end_date: str | None = None


class LanguageSkill(BaseModel):
    language: str
    fluency: str = Field(description="CEFR level (A1-C2) or 'Native'")


class CandidateProfile(BaseModel):
    name: str
    headline: str = Field(description="One-line professional identity, e.g. 'HR Analyst'")
    summary: str = Field(description="2-3 sentence professional summary")
    location: str | None = None
    work: list[WorkExperience]
    education: list[Education]
    skills: list[str] = Field(description="All named technologies, tools, methodologies")
    certificates: list[str] = Field(default_factory=list)
    languages: list[LanguageSkill] = Field(default_factory=list)


class CoverLatter(BaseModel):
    opening: str = Field(description="Opening paragraph")
    body: list[str] = Field(description="Body paragraphs")
    closing: str


class JobPosting(BaseModel):
    title: str = Field(description="Job title as published")
    company: str = Field(description="Hiring organization name")
    location: str | None = Field(default=None, description="City/country, or 'Remote'")
    employment_type: str | None = Field(default=None, description="Full-time, contract, etc.")
    responsibilities: list[str] = Field(description="Duties listed in the posting")
    qualifications: list[str] = Field(description="Required and preferred qualifications")
    skills: list[str] = Field(description="Named technologies, tools, certifications")
    raw_text: str = Field(description="Original posting text, for retrieval")


class Certificate(BaseModel):
    name: str = Field(description="Certification name as issued, e.g. 'Neural Networks and Deep Learning'")
    issuer: str = Field(description="Issuing organization, e.g. 'Coursera'")
    issue_date: str = Field(description="ISO format YYYY-MM")
    expiration_date: str | None = Field(
        default=None,
        description="ISO format YYYY-MM, or null if the credential does not expire",
    )
    credential_id: str | None = Field(
        default=None, description="Credential or licence number, if the issuer provides one"
    )
    credential_url: str | None = Field(
        default=None, description="Public verification link, if available"
    )
    skills: list[str] = Field(
        default_factory=list,
        description="Skills this credential attests to, matching JobPosting.skills vocabulary",
    )