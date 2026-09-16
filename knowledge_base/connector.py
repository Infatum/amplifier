from langchain_ollama import OllamaEmbeddings
import chromadb
import os

embeddings = OllamaEmbeddings(model="bge-m3")

def connect():
    chromadb_path = os.environ.get("CHROMADB_STORAGE", "./chroma_db")
    return chromadb.PersistentClient(path=chromadb_path)