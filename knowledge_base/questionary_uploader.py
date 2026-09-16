from knowledge_base.connector import connect, chromadb, embeddings
from prompt_templates import assignment_answers_prompt
from langchain_ollama.chat_models import ChatOllama
from langchain_core.documents import Document
from entities import Answers
import pandas as pd
import glob
import os


def load_excel_file(filepath: str):
    sheets = {}
    with pd.ExcelFile(filepath) as xls:
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet_name)
            sheets[sheet_name] = df.reset_index()
    return sheets


def filter_answers(question: str, column: pd.Series, model="gemma4:4b", temperature=0.):
    llm = ChatOllama(model="gemma4:4b", temperature=temperature)
    answer_filter = assignment_answers_prompt | llm.with_structured_output(Answers)
    answers = answer_filter.invoke({"header": question, "cells": column.to_list()})
    return answers


def upload_assignments(folder: str, vector_db_client: chromadb.Client):
    file_pattern = os.path.join(folder, "*.xlsx")
    all_excel_files = glob.glob(file_pattern)
    for file in all_excel_files:
        sheets = load_excel_file(file)
        for name, assignment in sheets.items():
            for question in assignment.columns:
                answers = filter_answers(question, assignment[question])
                store_answers(file, name, question, assignment, answers, vector_db_client)


def store_answers(file: str, name: str, question: str, data: pd.DataFrame, answers: Answers, vector_db: chromadb.Client):
    collection = vector_db.get_or_create_collection("Assignments")
    ids, documents, metadatas = [], [], []

    for cell in answers.column:
        if cell.is_a_question:
            continue
        text = str(data.iloc[cell.index]).strip()
        ids.append(f"{os.path.basename(file)}|{name}|{question}|{cell.index}")

        documents.append(f"Питання: {question}\nВідповідь: {text}")
        metadatas.append({
            "file": os.path.basename(file),
            "sheet": name,
            "question": question,
        })
        if documents:
            collection.upsert(
                ids=ids,
                documents=documents,
                embeddings=embeddings.embed_documents(documents),
                metadatas=metadatas,
            )