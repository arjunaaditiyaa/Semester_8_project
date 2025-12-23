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
