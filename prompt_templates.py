
from langchain_core.prompts import ChatPromptTemplate


answers_filtering_template = """Колонка анкети самоаналізу. Заголовок: {header}

Поверни лише ті клітинки, які є відповідями кандидата про себе
(перша особа, конкретика). Пропусти інструкції до заповнення
(наказовий спосіб, звертання на "ви") та переформульовані питання.

{cells}"""

candidate_cv_template = """Candidate curriculum vitae in Markdown:

{cv_text}

Extract the candidate profile from this resume.

Rules:
- Use only what is explicitly stated in the cv. Do not invent or infer anything.
- Keep the original wording. Do not translate or paraphrase.
- Write dates as YYYY-MM. If a position is current ("Present", "Current", "Now"), leave end_date empty.
- If there is no headline, use the most recent job title.
- If there is no summary, write 2-3 sentences in the same language as the resume, using only facts from it."""

assignment_answers_prompt = ChatPromptTemplate.from_template(answers_filtering_template)
cv_prompt = ChatPromptTemplate.from_template(candidate_cv_template)