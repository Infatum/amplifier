
from knowledge_base.connector import connect, embeddings
from langchain_pymupdf4llm import PyMuPDF4LLMLoader
from langchain_ollama.chat_models import ChatOllama
from prompt_templates import cv_prompt
from entities import CandidateProfile
import uuid
import os


def acquire_candidate_profile(
        model: str, document: PyMuPDF4LLMLoader, temperature: float=0.5
) -> CandidateProfile:
    llm = ChatOllama(model=model, temperature=temperature)
    chain = cv_prompt | llm.with_structured_output(CandidateProfile)
    profile = chain.invoke({"cv_text": document[0].page_content})   
    return profile


def load_cv(model: str, candidate_id: uuid.UUID, cv_file: str, temperature=0.):
    cv = PyMuPDF4LLMLoader(cv_file, mode="single").load()
    candidate = acquire_candidate_profile(model, cv, temperature)
    vector_db = connect()
    collection = vector_db.get_or_create_collection("Curriculum Vitae")
    doc_id = f"{candidate_id}|{candidate.headline}"
    metadata = {"file": os.path.basename(cv_file)}
    collection.upsert(
        ids=doc_id, documents=cv, embeddings=embeddings.embed_documents(cv), metadatas=metadata
    )