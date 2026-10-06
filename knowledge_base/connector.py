from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv
import chromadb
import os

load_dotenv()
embeddings = OllamaEmbeddings(model="bge-m3")
local_model = os.environ.get("LOCAL_MODEL")


def connect():
    chromadb_path = os.environ.get("CHROMADB_STORAGE", "./chroma_db")
    return chromadb.PersistentClient(path=chromadb_path)

# Collection names live here so a typo is an ImportError, not a silently
# created empty collection -- get_or_create_collection never complains.
CURRICULUM_VITAE = "CurriculumVitae"
PROFILING = "Profiling"
SEMAPHORE = "Semaphore"
PLANS = "Plans"
ROLES = "Roles"


def open_store(collection_name: str) -> Chroma:
    return Chroma(
        client=connect(),
        collection_name=collection_name,
        embedding_function=embeddings,
        collection_metadata={"hnsw:space": "cosine"},
    )
