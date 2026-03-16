from os import getenv
from fastapi import FastAPI, HTTPException, Depends, status
from sqlmodel import SQLModel, select, create_engine, Field, Session
from typing import Optional, List, Annotated, Dict
from dotenv import load_dotenv
from urllib.parse import unquote
from pydantic import ValidationError


from usefulapi import UsefulAPI


load_dotenv()

USERNAME = getenv("USERNAME")
PASSWORD = getenv("PASSWORD")
IP = getenv("IP")
PORT = getenv("PORT", default="5432")
DBNAME = getenv("DBNAME")


engine = create_engine(f"postgresql://{USERNAME}:{PASSWORD}@{IP}:{PORT}/{DBNAME}")

class ProductBase(SQLModel):
    name: str
    description: Optional[str] = None
    price: float = Field(gt=0)
    content: str

class Product(ProductBase, table=True):
    __tablename__ = "products"
    id: int = Field(default=None, primary_key=True)

class ProductGet(ProductBase):
    id: int

class ProductAdd(ProductBase):
    pass

class ProductSet(ProductBase):
    name: Optional[str] = None
    price: Optional[float] = None
    content: Optional[str] = None

app = FastAPI()

def connect_to_db():
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()

def get_params(filter: str | None = "id gt -1", sort: str | None = "id", page: int | None = 1, limit: int | None = None):
    filter = unquote(filter)
    sort = unquote(sort)
    return {"filter": filter,
            "sort": sort,
            "page": page - 1,
            "limit": limit,
            "offset": (page - 1)* (limit or 0)}

db_annotation = Annotated[Session, Depends(connect_to_db)]
url_params = Annotated[Dict[str, str | int], Depends(get_params)]

@app.get("/products", response_model=List[ProductGet])
def get_products(db: db_annotation, params: url_params):
    fields = ["id", "name", "description", "price", "content"]
    statement = select(Product)
    statement = UsefulAPI.all_in_one(statement, Product,
                                    params["filter"],
                                    params["sort"],
                                    fields,
                                    params["page"],
                                    params["limit"])
    data = db.exec(statement).all()
    return data

@app.get("/products/{id}", response_model=ProductGet)
def get_product(db: db_annotation, id: int):
    data = db.get(Product, id)
    if data:
        return data
    else:
        raise HTTPException(detail=f"Wrong id {id}, nothing here", status_code=status.HTTP_404_NOT_FOUND)

@app.post("/products", response_model=ProductGet)
def add_product(value: ProductAdd, db: db_annotation):
    data = Product(**value.model_dump())
    if data:
        db.add(data)
        db.commit()
        db.refresh(data)
        return data
    db.rollback()

@app.put("/products/{id}", response_model=ProductGet)
def set_product(id: int, value: ProductSet, db: db_annotation):
    data = db.get(Product, id)
    if data:
        for _i, _v in value.model_dump().items():
            setattr(data, _i, _v)
        db.add(data)
        db.commit()
        db.refresh(data)
        return data
    else:
        try:
            data = Product(**value.model_dump())
            if data:
                db.add(data)
                db.commit()
                db.refresh(data)
                return data
            db.rollback()
        except ValidationError as e:
            raise HTTPException(detail=f"An error raised detail: {e}", status_code=status.HTTP_422_UNPROCESSABLE_CONTENT)
        db.rollback()

@app.delete("/products/{id}")
def delete_product(id: int, db: db_annotation):
    data = db.get(Product, id)
    if data:
        db.delete(data)
        db.commit()
        return id
    else:
        raise HTTPException(detail=f"Product {id} not found!", status_code=status.HTTP_404_NOT_FOUND)