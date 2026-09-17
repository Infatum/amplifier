
from knowledge_base.connector import connect, embeddings
from langchain_pymupdf4llm import PyMuPDF4LLMLoader
from langchain_chroma import Chroma
import uuid
import os


def insert_cv(candidate_id: uuid.UUID, cv_file: str):
    store = Chroma(
        client=connect(), 
        collection_name="CurriculumVitae", 
        embedding_function=embeddings, 
        collection_metadata={"hnsw:space": "cosine"},
    )
    cv = PyMuPDF4LLMLoader(cv_file, mode="single", use_layout=False).load()
    for doc in cv:
        doc.id = f"{candidate_id}|{os.path.basename(cv_file)}"
        doc.metadata |= {"candidate_id": str(candidate_id)}
        store.add_documents(cv)