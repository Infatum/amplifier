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


def open_store(collection_name: str) -> Chroma:
    return Chroma(
        client=connect(),
        collection_name=collection_name,
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


def store_assignments(candidate_id: uuid.UUID, folder: str, model: str):
    file_pattern = os.path.join(folder, "*.xlsx")
    all_excel_files = glob.glob(file_pattern)

    for file in all_excel_files:
        assignments = load_excel_file(file)
        profiling = assignments["Я-Профі"]
        store_profiling(candidate_id, file, profiling, model)
        semafor = assignments["Світлофор"]

       
def store_profiling(candidate_id: uuid.UUID, file: str, profiling: dict[pd.DataFrame], model: str, store):
     for question in profiling.columns:
        answers = filter_answers(question, profiling[question], model)
        insert_profiling(candidate_id, file, "Я-Профі", question, profiling, answers)


def build_document(candidate_id: uuid.UUID, cell_id: int, file: str, name: str, question: str, topic: str, page_content: str) -> list[Document]:
    return Document(
        page_content=page_content,
        metadata={
            "candidate_id": str(candidate_id),
            "file": os.path.basename(file),
            "sheet": name,
            "question": question,
            "topic": topic,
        },
        id=f"{candidate_id}|{name}|{question}|{cell_id}",
    )


def insert_semaphore(candidate_id: uuid.UUID, file: str, name: str, data: pd.DataFrame) -> list[Document]:
    documents = []
    store = open_store("Semaphore")
    semaphor = get_semaphore(data)
    answers = data.drop(columns=[name])
    
    for i in range(1, len(data)):
        question = str(data.iloc[i][name])
        answer = answers.iloc[i][1:]
        contents = semaphore_answer(semaphor, question, answer)
        for color, topic, page_content in contents:
            documents.append(build_document(candidate_id, f"{color}|{i}", file, name, question, topic, page_content))
    store.add_documents(documents)


def semaphore_answer(semaphor: dict, question: str,  answer: pd.Series):
    g_elab, y_elab, r_elab = semaphor["green"]["elaboration"], semaphor["yellow"]["elaboration"], semaphor["red"]["elaboration"]
    colors = {"green": semaphor["green"]["color"], "yellow": semaphor["yellow"]["color"], "red": semaphor["red"]["color"]}
    contents = (
        (
            "green", f"Питання: {question} ({g_elab})", f"Питання: {question}\nВідповідь({g_elab}): {str(answer[colors['green']])}"
        ),
        (
            "yellow", f"Питання: {question} ({y_elab})", f"Питання: {question}\nВідповідь({y_elab}): {str(answer[colors['yellow']])}"
        ),
        (
            "red", f"Питання: {question} ({r_elab})", f"Питання: {question}\nВідповідь({r_elab}): {str(answer[colors['red']])}"
        ),
    )
    return contents


def get_semaphore(data: pd.DataFrame):
    return {
        "green": {
            "color": data.columns[2], "elaboration": str(data.iloc[0, 2])
            }
        ,
        "yellow": {
            "color": data.columns[3], "elaboration": str(data.iloc[0, 3])
            }
        ,
        "red": {
            "color": data.columns[4], "elaboration": str(data.iloc[0, 4])
        }
    }


def insert_profiling(
    candidate_id: uuid.UUID, file: str, name: str, question: str, data: pd.DataFrame, answers: Answers
):
    store = open_store("Profiling")
    for cell in answers.column:
        if cell.is_a_question:
            continue
        text = str(data[question].loc[cell.id]).strip()
        documents = []
        for cell in answers.column:
            page_content = f"Питання: {question}\nВідповідь: {text}",
            if cell.is_a_question:
                continue
            text = str(data[question].loc[cell.id]).strip()
            documents.append(
                build_document(
                    candidate_id, f"{candidate_id}|{name}|{question}|{cell.id}", file, name, question, cell.topic, page_content
                )
            )
    if documents:
        store.add_documents(documents)
