from knowledge_base.cv_uploader import load_cv
import uuid
import os

candidate_id = uuid.UUID('1b313ceb9d4f4922a317ab985f72607c')
model = os.environ.get("LOCAL_MODEL")

load_cv(candidate_id, "./cv/Anna_Vitiuk_CV_Senior_AI_Engineer.pdf")