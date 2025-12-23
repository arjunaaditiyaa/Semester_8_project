import json
import requests
from typing import Optional, List, Type
from datetime import datetime
from sqlmodel import SQLModel, Field, create_engine, Session, select
from openai import OpenAI


class VaccinationSchedule(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    target_disease: str
    age_group: str
    schedule_details: str

class SymptomGuide(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    disease_name: str
    common_symptoms: str
    prevention: str

class DiseaseOutbreak(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    summary: str
    publication_date: str
    url: str


engine = create_engine("sqlite:///healthcare_expert.db")
def init_db():

    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:

        if not session.exec(select(VaccinationSchedule)).first():
            session.add(VaccinationSchedule(target_disease="Polio", age_group="Infants",
                                            schedule_details="4 doses at 2, 4, 6-18 months, and 4-6 years."))
            session.add(VaccinationSchedule(target_disease="Hepatitis B", age_group="Infants",
                                            schedule_details="3 doses: Birth, 1-2 months, 6-18 months."))


        if not session.exec(select(SymptomGuide)).first():
            session.add(
                SymptomGuide(disease_name="Cholera", common_symptoms="Severe watery diarrhea, vomiting, leg cramps.",
                             prevention="Safe water, handwashing, vaccine."))
            session.add(
                SymptomGuide(disease_name="Mpox", common_symptoms="Rash with blisters, fever, swollen lymph nodes.",
                             prevention="Avoid skin contact with infected, vaccination."))
        session.commit()