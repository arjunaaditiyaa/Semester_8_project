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

def sync_who_outbreaks():
    API_URL = "https://www.who.int/api/news/diseaseoutbreaknews"
    print("🔄 Syncing with WHO Outbreak Database...")
    try:
        response = requests.get(API_URL, timeout=10)
        data = response.json()

        items = data.get('value', [])[:10]

        with Session(engine) as session:
            for item in items:
                existing = session.exec(select(DiseaseOutbreak).where(DiseaseOutbreak.title == item['Title'])).first()
                if not existing:
                    new_outbreak = DiseaseOutbreak(
                        title=item['Title'],
                        summary=item.get('Overview', 'No summary provided.'),
                        publication_date=item.get('PublicationDate', 'Unknown'),
                        response=item.get('Response','no response provoided'),
                        further_info=item.get('FurtherInformation','no further information'),
                        url=f"https://www.who.int/emergencies/disease-outbreak-news/item/{item.get('ItemDefaultUrl', '')}"
                    )
                    session.add(new_outbreak)
            session.commit()
        return f"Successfully synced {len(items)} latest WHO reports."
    except Exception as e:
        return f"API Sync Error: {str(e)}"

def get_vaccine_schedule(disease: str) -> str:
    with Session(engine) as session:
        statement = select(VaccinationSchedule).where(VaccinationSchedule.target_disease.contains(disease))
        results = session.exec(statement).all()
        return json.dumps(
            [r.model_dump() for r in results]) if results else "No vaccination schedule found in database."


def get_disease_symptoms(disease: str) -> str:
    with Session(engine) as session:
        statement = select(SymptomGuide).where(SymptomGuide.disease_name.contains(disease))
        results = session.exec(statement).all()
        return json.dumps([r.model_dump() for r in results]) if results else "No symptom info found."


def check_active_outbreaks(query: str) -> str:
    with Session(engine) as session:
        statement = select(DiseaseOutbreak).where(DiseaseOutbreak.title.contains(query))
        results = session.exec(statement).all()
        return json.dumps([r.model_dump() for r in results]) if results else "No active outbreaks found for that query."
