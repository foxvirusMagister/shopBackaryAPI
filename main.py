from os import getenv
from fastapi import FastAPI, HTTPException
from sqlmodel import SQLModel, select, create_engine, Field, Session
from typing import Optional, List
from dotenv import load_dotenv

load_dotenv()

USERNAME = load_dotenv("USERNAME")
PASSWORD = load_dotenv("PASSWORD")
IP = load_dotenv("IP")
PORT = load_dotenv("IP") if load_dotenv("IP") != "" else "5432"
DBNAME = load_dotenv("DBNAME")


engine = create_engine(f"postgresql://{USERNAME}:{PASSWORD}@{IP}/{DBNAME}")

class ProductBase(SQLModel):
    name: str
    description: Optional[str] = None
    price: float
    content: str

class Product(ProductBase, table=True):
    __tablename__ = "products"
    id: int = Field(default=None, primary_key=True)

class ProductAdd(ProductBase):
    pass

class ProductSet(ProductBase):
    name: Optional[str] = None
    price: Optional[float] = None
    content: Optional[str] = None

app = FastAPI()

@app.get("/products", response_model=List[Product])
def get_products():
    with Session(engine) as session:
        data = session.exec(select(Product)).all()
        return data