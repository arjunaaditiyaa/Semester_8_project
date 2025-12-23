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

class HealthAgent:
    def __init__(self):
        self.client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
        self.model = "llama3.1"
        self.tools = {
            "get_vaccine_schedule": get_vaccine_schedule,
            "get_disease_symptoms": get_disease_symptoms,
            "check_active_outbreaks": check_active_outbreaks,
            "sync_who_outbreaks": sync_who_outbreaks
        }

    def chat(self, user_prompt: str):
        print(f"\nUser: {user_prompt}")

        system_msg = (
            "You are a Multilingual Healthcare Assistant. Respond in the user's language. "
            "Use the provided tools to get verified medical facts. "
            "ALWAYS include a disclaimer: 'I am an AI, not a doctor. Consult a professional.'"
        )

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_prompt}
        ]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            functions=[
                {"name": "get_vaccine_schedule",
                 "parameters": {"type": "object", "properties": {"disease": {"type": "string"}}}},
                {"name": "get_disease_symptoms",
                 "parameters": {"type": "object", "properties": {"disease": {"type": "string"}}}},
                {"name": "check_active_outbreaks",
                 "parameters": {"type": "object", "properties": {"query": {"type": "string"}}}},
                {"name": "sync_who_outbreaks", "parameters": {"type": "object", "properties": {}}}
            ]
        )

        message = response.choices[0].message

        if message.function_call:
            fn_name = message.function_call.name
            fn_args = json.loads(message.function_call.arguments)
            print(f" Agent calling tool: {fn_name}({fn_args})")

            tool_result = self.tools[fn_name](**fn_args)

            messages.append(message)
            messages.append({"role": "function", "name": fn_name, "content": tool_result})

            final_response = self.client.chat.completions.create(
                model=self.model,
                messages=messages
            )
            print(f"Assistant: {final_response.choices[0].message.content}")
        else:
            print(f"Assistant: {message.content}")


if __name__ == "__main__":
    init_db()
    agent = HealthAgent()

    agent.chat("¿Cuáles son los síntomas del Cólera?")

    agent.chat("Sync the latest WHO outbreaks and tell me if there is any news about Mpox.")

    agent.chat("What is the vaccination schedule for Polio?")
