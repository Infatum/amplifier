from langchain_ollama import OllamaEmbeddings
from dotenv import load_dotenv
import chromadb
import os

load_dotenv()
embeddings = OllamaEmbeddings(model="bge-m3")
local_model = os.environ.get("LOCAL_MODEL")


def connect():
    chromadb_path = os.environ.get("CHROMADB_STORAGE", "./chroma_db")
    return chromadb.PersistentClient(path=chromadb_path)