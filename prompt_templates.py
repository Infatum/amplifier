
from langchain_core.prompts import ChatPromptTemplate


answers_filtering_template = """Колонка анкети самоаналізу. Заголовок: {header}

Поверни лише ті клітинки, які є відповідями кандидата про себе
(перша особа, конкретика). Пропусти інструкції до заповнення
(наказовий спосіб, звертання на "ви") та переформульовані питання.

{cells}"""

assignment_answers_prompt = ChatPromptTemplate(answers_filtering_template)