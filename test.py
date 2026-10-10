from knowledge_base.profiling_uploader import insert_semaphore
from knowledge_base.utils import load_excel_file
from knowledge_base.profiling_uploader import store_assignments
from knowledge_base.connector import local_model
import uuid
import os

candidate_id = uuid.UUID('1b313ceb9d4f4922a317ab985f72607c')

data = load_excel_file("./my_assignments/ТЗ на пошук роботи.xlsx")
insert_semaphore(candidate_id, "./my_assignments/ТЗ на пошук роботи.xlsx", 'Світлофор', data['Світлофор'])