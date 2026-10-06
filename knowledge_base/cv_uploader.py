
from knowledge_base.connector import open_store, CURRICULUM_VITAE
from langchain_pymupdf4llm import PyMuPDF4LLMLoader
import uuid
import os


def insert_cv(candidate_id: uuid.UUID, cv_file: str):
    store = open_store(CURRICULUM_VITAE)
    cv = PyMuPDF4LLMLoader(cv_file, mode="single", use_layout=False).load()
    for doc in cv:
        doc.id = f"{candidate_id}|{os.path.basename(cv_file)}"
        doc.metadata |= {"candidate_id": str(candidate_id)}
        store.add_documents(cv)