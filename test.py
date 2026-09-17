from knowledge_base.connector import local_model
from knowledge_base.cv_uploader import insert_cv
import uuid
import os

candidate_id = uuid.UUID('1b313ceb9d4f4922a317ab985f72607c')

insert_cv(local_model, candidate_id, "./cv/Anna_Vitiuk_CV_Senior_AI_Engineer.pdf", temperature=0.1)