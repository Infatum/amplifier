from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv
import chromadb
import os

load_dotenv()
PLANS = "Plans"
ROLES = "Roles"
PROFILING = "Profiling"
SEMAPHORE = "Semaphore"
CURRICULUM_VITAE = "CurriculumVitae"
local_model = os.environ.get("LOCAL_MODEL")
embeddings = OllamaEmbeddings(model="bge-m3")


def connect():
    chromadb_path = os.environ.get("CHROMADB_STORAGE", "./chroma_db")
    return chromadb.PersistentClient(path=chromadb_path)


def open_store(collection_name: str) -> Chroma:
    return Chroma(
        client=connect(),
        collection_name=collection_name,
        embedding_function=embeddings,
        collection_metadata={"hnsw:space": "cosine"},
    )
