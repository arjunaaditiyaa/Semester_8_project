import requests
from typing import Optional
from sqlmodel import SQLModel, Field, create_engine, Session, select
from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

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
            session.add(VaccinationSchedule(
                target_disease="Polio",
                age_group="Infants",
                schedule_details="4 doses at 2, 4, 6–18 months, and 4–6 years."
            ))
        if not session.exec(select(SymptomGuide)).first():
            session.add(SymptomGuide(
                disease_name="Cholera",
                common_symptoms="Severe watery diarrhea, vomiting, leg cramps.",
                prevention="Safe water, handwashing, vaccine."
            ))
        session.commit()

def sync_who_outbreaks():
    url = "https://www.who.int/api/news/diseaseoutbreaknews"
    response = requests.get(url, timeout=10).json()
    items = response.get("value", [])[:10]
    with Session(engine) as session:
        for item in items:
            exists = session.exec(
                select(DiseaseOutbreak).where(DiseaseOutbreak.title == item["Title"])
            ).first()
            if not exists:
                session.add(DiseaseOutbreak(
                    title=item["Title"],
                    summary=item.get("Overview", "No summary"),
                    publication_date=item.get("PublicationDate", "Unknown"),
                    url=f"https://www.who.int/emergencies/disease-outbreak-news/item/{item.get('ItemDefaultUrl','')}"
                ))
        session.commit()
    return "WHO data synced"

def get_vaccine_schedule(disease):
    with Session(engine) as session:
        results = session.exec(
            select(VaccinationSchedule).where(
                VaccinationSchedule.target_disease.contains(disease)
            )
        ).all()
    return "\n".join(r.schedule_details for r in results) or "No data found"

def get_disease_symptoms(disease):
    with Session(engine) as session:
        results = session.exec(
            select(SymptomGuide).where(
                SymptomGuide.disease_name.contains(disease)
            )
        ).all()
    return "\n".join(r.common_symptoms for r in results) or "No data found"

def check_active_outbreaks(query):
    with Session(engine) as session:
        results = session.exec(
            select(DiseaseOutbreak).where(
                DiseaseOutbreak.title.contains(query)
            )
        ).all()
    return "\n".join(r.title for r in results) or "No outbreaks found"

class HealthAgent:
    def __init__(self):
        self.client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

    def chat(self, prompt):
        response = self.client.chat.completions.create(
            model="llama3.1",
            messages=[
                {"role": "system", "content": "You are a healthcare assistant. Always say: I am an AI, not a doctor."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content

agent = HealthAgent()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Use /ask, /vaccine, /symptoms, /outbreak, /sync")

async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(agent.chat(" ".join(context.args)))

async def vaccine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_vaccine_schedule(" ".join(context.args)))

async def symptoms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_disease_symptoms(" ".join(context.args)))

async def outbreak(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(check_active_outbreaks(" ".join(context.args)))

async def sync(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(sync_who_outbreaks())

def main():
    init_db()
    app = ApplicationBuilder().token("8317797295:AAFGLEWIcLuSSW5zRgJ9t2CtAe5vv8dqht8").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ask", ask))
    app.add_handler(CommandHandler("vaccine", vaccine))
    app.add_handler(CommandHandler("symptoms", symptoms))
    app.add_handler(CommandHandler("outbreak", outbreak))
    app.add_handler(CommandHandler("sync", sync))

    app.run_polling()

if __name__ == "__main__":
    main()
