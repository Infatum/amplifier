from knowledge_base.connector import connect, embeddings
from prompt_templates import assignment_answers_prompt
from langchain_ollama.chat_models import ChatOllama
from langchain_core.documents import Document
from langchain_chroma import Chroma
from entities import Answers
import pandas as pd
import glob
import uuid
import os


def open_store() -> Chroma:
    return Chroma(
        client=connect(),
        collection_name="Assignments",
        embedding_function=embeddings,
        collection_metadata={"hnsw:space": "cosine"},
    )


def load_excel_file(filepath: str):
    sheets = {}
    with pd.ExcelFile(filepath) as xls:
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet_name)
            sheets[sheet_name] = df.reset_index()
    return sheets


def filter_answers(question: str, column: pd.Series, model: str, temperature=0.):
    llm = ChatOllama(model=model, temperature=temperature)
    answer_filter = assignment_answers_prompt | llm.with_structured_output(Answers)
    answers = answer_filter.invoke({"header": question, "cells": column.to_list()})
    return answers


def insert_assignments(candidate_id: uuid.UUID, folder: str, model: str):
    file_pattern = os.path.join(folder, "*.xlsx")
    all_excel_files = glob.glob(file_pattern)
    store = open_store()
    
    for file in all_excel_files:
        sheets = load_excel_file(file)
        for name, assignment in sheets.items():
            for question in assignment.columns:
                answers = filter_answers(question, assignment[question], model)
                store_answers(candidate_id, file, name, question, assignment, answers, store)


def build_documents(
    candidate_id: uuid.UUID, file: str, name: str, question: str, data: pd.DataFrame, answers: Answers
) -> list[Document]:
    documents = []
    for cell in answers.column:
        if cell.is_a_question:
            continue
        text = str(data[question].loc[cell.id]).strip()
        documents.append(
            Document(
                page_content=f"Питання: {question}\nВідповідь: {text}",
                metadata={
                    "candidate_id": str(candidate_id),
                    "file": os.path.basename(file),
                    "sheet": name,
                    "question": question,
                    "topic": cell.topic,
                },
                id=f"{candidate_id}|{name}|{question}|{cell.id}",
            )
        )
    return documents


def store_answers(
    candidate_id: uuid.UUID, file: str, name: str, question: str, data: pd.DataFrame, answers: Answers, store: Chroma
):
    documents = build_documents(candidate_id, file, name, question, data, answers)
    if documents:
        store.add_documents(documents)
