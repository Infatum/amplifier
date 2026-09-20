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


def insert_semafor(candidate_id: uuid.UUID, file: str, name: str, question: str, data: pd.DataFrame) -> list[Document]:
    documents = []
    answers = []
    store = open_store("Semafore")

    data = data.set_index(name)
    answers = data.iloc[2:]
    semafor = get_semaphore(data)
    index = 2
    
    
    for question, answer in answers.iterrows():
        question = str(question)
        contents = semaphore_answer(semafor, question, answer)
        for page_content in contents:
            topic, content = page_content
            documents.append(build_document(candidate_id, index, file, name, question, topic, content))
    store.add_documents(documents)


def semaphore_answer(semaphor: dict, question: str,  answer: pd.Series):
    green_elaboration = answer[semaphor["green"]["elaboration"]]
    yellow_elaboration = answer[semaphor["yellow"]["elaboration"]]
    red_elaboration = answer[semaphor["red"]["elaboration"]]
    namings = {"green": semaphor["green"]["color"], "yellow": semaphor["yellow"]["color"], "red": semaphor["yellow"]["color"]}
    contents = {
        {f"Питання: {question}: {green_elaboration}", f"Питання: {question}\nВідповідь: {namings['green']}({green_elaboration})\n{str(answer[namings['green']])}"},
        {f"Питання: {question}: {yellow_elaboration}", f"Питання: {question}\nВідповідь: {namings['yellow']}({yellow_elaboration})\n{str(answer[namings['yellow']])}"},
        {f"Питання: {question}: {red_elaboration}", f"Питання: {question}\nВідповідь: {namings['red']}({red_elaboration})\n{str(answer[namings['red']])}"},
    }
    return contents


def get_semaphore(data: pd.DataFrame):
    return {
        "green": {
            "color": data.columns[0], "elaboration": data.iloc[0][1]
            }
        ,
        "yellow": {
            "color": data.columns[1], "elaboration": data.iloc[1][1]
            }
        ,
        "red": {
            "color": data.columns[2], "elaboration": data.iloc[2][1]
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
