from knowledge_base.questionary_uploader import open_store, load_excel_file
from langchain_core.documents import Document
import pandas as pd
import uuid
import os


def get_plans(data: pd.DataFrame):
    plans = {}
    for column in data.columns[2:5]:
        title, _, timeframe = str(column).partition("\n")
        plans[title.strip()] = {"column": column, "timeframe": timeframe.strip()}
    return plans


def plan_answer(plans: dict, marker: str, row: pd.Series):
    contents = []
    for title, plan in plans.items():
        value = row[plan["column"]]
        if pd.isna(value):
            continue
        contents.append((
            title,
            f"{marker} ({title})",
            f"Критерій: {marker}\n{title} — {plan['timeframe']}: {str(value).strip()}",
        ))
    return tuple(contents)


def build_plan_document(candidate_id, file, name, marker, section, deadline, title, i, topic, page_content):
    return Document(
        page_content=page_content,
        metadata={
            "candidate_id": str(candidate_id),
            "file": os.path.basename(file),
            "sheet": name,
            "question": marker,
            "topic": topic,
            "section": section,
            "plan": title,
            "deadline": deadline,
        },
        id=f"{candidate_id}|{name}|{marker}|{title}|{i}",
    )


def insert_plan(candidate_id: uuid.UUID, file: str, name: str, data: pd.DataFrame):
    documents = []
    store = open_store("Plans")
    markers = data.columns[1]
    deadline = str(markers).strip()
    plans = get_plans(data)
    section = ""

    for i in range(len(data)):
        if pd.isna(data.iloc[i][markers]):
            continue
        marker = str(data.iloc[i][markers]).strip()
        contents = plan_answer(plans, marker, data.iloc[i])
        if not contents:
            section = marker
            continue
        for title, topic, page_content in contents:
            documents.append(build_plan_document(
                candidate_id, file, name, marker, section, deadline, title, i, topic, page_content
            ))
    store.add_documents(documents)
