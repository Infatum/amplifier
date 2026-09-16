from langchain_pymupdf4llm import PyMuPDF4LLMLoader
from langchain_ollama.chat_models import ChatOllama
from connector import connect, embeddings
from prompt_templates import cv_prompt
from entities import CandidateProfile
import uuid
import os


def acquire_candidate_profile(document, temperature=0.5) -> CandidateProfile:
    llm = ChatOllama(model="gemma4:4b", temperature=temperature)
    chain = cv_prompt | llm.with_structured_output(CandidateProfile)
    profile = chain.invoke({"cv_text": document.page_content})   
    return profile


def load_cv(candatidate_id: uuid.UUID, cv_file: str, temperature=0.):
    cv = PyMuPDF4LLMLoader(cv_file, mode="single").load()
    candidate = acquire_candidate_profile(cv, temperature)
    vector_db = connect()
    collection = vector_db.get_or_create_collection("Curriculum Vitae")
    doc_id = f"{candatidate_id}|{candidate.headline}"
    metadata = {"file": os.path.basename(cv_file)}
    collection.upsert(
        ids=doc_id, documents=cv, embeddings=embeddings.embed_documents(cv), metadatas=metadata
    )