from langchain_ollama.chat_models import ChatOllama
from langchain_core.documents import Document
from prompt_templates import cv_prompt
from entities import CandidateProfile


def acquire_candidate_profile(
        model: str, document: list[Document], temperature: float=0.5
) -> CandidateProfile:
    llm = ChatOllama(model=model, temperature=temperature)
    chain = cv_prompt | llm.with_structured_output(CandidateProfile)
    profile = chain.invoke({"cv_text": document[0].page_content})   
    return profile