from os import getenv
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import SQLModel, select, create_engine, Field, Session
from sqlmodel import Relationship
from typing import Optional, List, Annotated, Dict
from dotenv import load_dotenv
from urllib.parse import unquote
from pydantic import ValidationError
from sqlalchemy.orm import selectinload
import bcrypt
from sqlalchemy.exc import IntegrityError
from psycopg2.errors import UniqueViolation
from pydantic import BaseModel
import boto3
from datetime import datetime, timezone, timedelta
import jwt
from jwt.exceptions import InvalidTokenError



from usefulapi import UsefulAPI


load_dotenv()

SECRET_KEY = "ebd1e720af063beac77e0dedc9e0749e783a48ddeb79218364ea7030eca5b949"

USERNAME = getenv("USERNAME")
PASSWORD = getenv("PASSWORD")
IP = getenv("IP")
PORT = getenv("PORT", default="5432")
DBNAME = getenv("DBNAME")
ADMIN_ROLE = getenv("ADMIN_ROLE")

oauth_form = OAuth2PasswordBearer(tokenUrl="token")

REGION = getenv("REGION")
AWS_ACCESS_ID = getenv("AWS_ACCESS_ID")
AWS_TENANT = getenv("AWS_TENANT")
AWS_SECRET_ACCESS_KEY = getenv("AWS_SECRET_ACCESS_KEY")
ENDPOINT_URL = getenv("ENDPOINT_URL")
BUCKET = getenv("BUCKET")

client = boto3.client("s3",
                   region_name=REGION,
                   aws_access_key_id=f"{AWS_TENANT}:{AWS_ACCESS_ID}",
                   aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                   endpoint_url=ENDPOINT_URL
                   )

bucket = BUCKET


engine = create_engine(f"postgresql://{USERNAME}:{PASSWORD}@{IP}:{PORT}/{DBNAME}")

class ProductBase(SQLModel):
    name: str
    price: float = Field(gt=0)
    content: str
    picture_key: Optional[str] = "default"
    category_id: Optional[int] = Field(default=None, foreign_key="categories.id") # Внешний ключ, нужен для сверения айди(наверное)

    

class Product(ProductBase, table=True):
    __tablename__ = "products"
    id: Optional[int] = Field(default=None, primary_key=True)

    category: Optional["Category"] = Relationship(back_populates="products") # Отношение между продуктом и категорией, нужно только для разработчика, в ответе не показывается

class ProductGet(ProductBase):
    id: int
    category: Optional[str] = None

class ProductAdd(ProductBase):
    pass

class ProductSet(ProductBase):
    name: Optional[str] = None
    price: Optional[float] = None
    content: Optional[str] = None
    picture_key: Optional[str] = None


class CategoryBase(SQLModel):
    name: str

class Category(CategoryBase, table=True):
    __tablename__ = "categories"
    id: int = Field(default=None, primary_key=True)

    products: List["Product"] = Relationship(back_populates="category")

class CategoryGet(CategoryBase):
    id: int

class CategoryAdd(CategoryBase):
    pass

class CategorySet(CategoryBase):
    name: Optional[str] = None


class UserBase(SQLModel):
    name: str
    role_id: int = Field(default=2, foreign_key="roles.id")

class User(UserBase, table=True):
    __tablename__ = "users"
    id: int = Field(default=None, primary_key=True)
    password_hash: str

    role: Optional["Role"] = Relationship(back_populates="users")

class UserAdd(UserBase):
    password_hash: str

class UserGet(UserBase):
    id: int

class UserSet(UserBase):
    name: Optional[str] = None
    role_id: Optional[int] = None
    password_hash: Optional[str] = None


class RoleBase(SQLModel):
    name: str
    can_add: Optional[bool] = False
    can_edit: Optional[bool] = False
    can_delete: Optional[bool] = False
    can_buy: Optional[bool] = True

class Role(RoleBase, table=True):
    __tablename__ = "roles"
    id: int = Field(default=None, primary_key=True)

    users: List[User] = Relationship(back_populates="role")

class RoleGet(RoleBase):
    id: int

class RoleAdd(RoleBase):
    pass

class RoleSet(RoleBase):
    name: Optional[str] = None
    can_add: Optional[bool] = None
    can_edit: Optional[bool] = None
    can_delete: Optional[bool] = None
    can_buy: Optional[bool] = None


class UsersPassword(BaseModel):
    username: str
    password: str


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


jwt_dep = Annotated[str, Depends(oauth_form)]
db_annotation = Annotated[Session, Depends(connect_to_db)]
url_params = Annotated[Dict[str, str | int], Depends(get_params)]

def get_current_user(db: db_annotation, token: jwt_dep) -> User:
    creds_exception = HTTPException(detail="Can't validate creditions",
                                    status_code=status.HTTP_401_UNAUTHORIZED,
                                    headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except InvalidTokenError:
        raise creds_exception
    statement = select(User).where(User.name == payload["username"])
    user = db.exec(statement).first()
    if user:
        return user
    raise creds_exception

user_dep = Annotated[User, Depends(get_current_user)]

@app.get("/products", response_model=List[ProductGet])
def get_products(db: db_annotation, params: url_params):
    fields = ["id", "name", "description", "price", "content", "category_id"]
    statement = select(Product)
    statement = UsefulAPI.all_in_one(statement, Product,
                                    params["filter"],
                                    params["sort"],
                                    fields,
                                    params["page"],
                                    params["limit"]).options(selectinload(Product.category))
    data = db.exec(statement).all()
    result = []
    for product in data:
        temp = dict(**product.model_dump())
        temp["category"] = product.category.name
        result.append(temp)
    return result

@app.get("/products/link/{id}")
def get_pic_link(db: db_annotation, id: int):
    data = db.get(Product, id)
    link = client.generate_presigned_url("get_object",
                                            Params={"Bucket": bucket,
                                                    "Key": data.picture_key},
                                            ExpiresIn=180)
    if link:
        return link
    raise HTTPException(detail="Key of picture is incorrect", status_code=status.HTTP_404_NOT_FOUND)


@app.get("/products/{id}", response_model=ProductGet)
def get_product(db: db_annotation, id: int):
    data = db.get(Product, id)
    if data:
        result = dict(**data.model_dump())
        result["category"] = data.category.name
        return result
    else:
        raise HTTPException(detail=f"Wrong id {id}, nothing here", status_code=status.HTTP_404_NOT_FOUND)

@app.post("/products")
def add_product(value: ProductAdd, db: db_annotation, current_user: user_dep):
    if current_user.role.name != "admin":
        raise HTTPException(detail="Wrong role", status_code=status.HTTP_401_UNAUTHORIZED)
    data = Product(**value.model_dump())
    if data:
        db.add(data)
        db.commit()
        db.refresh(data)
        return data
    db.rollback()

@app.get("/products/link/post/{key}")
def get_link_to_post(key: str, db: db_annotation, current_user: user_dep):
    if current_user.role.name != "admin":
        raise HTTPException(detail="Wrong role", status_code=status.HTTP_401_UNAUTHORIZED)
    statement = select(Product).filter(Product.picture_key == key)
    user = db.exec(statement).first()
    if user:
        link = client.generate_presigned_url("put_object",
                                    Params={"Bucket": bucket,
                                            "Key": key},
                                    ExpiresIn=180)
        return link
    raise HTTPException(detail=f"Product with key {key} not found!", status_code=status.HTTP_404_NOT_FOUND)
    

@app.put("/products/{id}")
def set_product(id: int, value: ProductSet, db: db_annotation, current_user: user_dep):
    if current_user.role.name != "admin":
        raise HTTPException(detail="Wrong role", status_code=status.HTTP_401_UNAUTHORIZED)
    data = db.get(Product, id)
    if data:
        for _i, _v in value.model_dump().items():
            if _v != None: setattr(data, _i, _v)
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
            db.rollback()
            raise HTTPException(detail=f"An error raised detail: {e}", status_code=status.HTTP_422_UNPROCESSABLE_CONTENT)
        db.rollback()

@app.delete("/products/{id}")
def delete_product(id: int, db: db_annotation, current_user: user_dep):
    if current_user.role.name != "admin":
        raise HTTPException(detail="Wrong role", status_code=status.HTTP_401_UNAUTHORIZED)
    data = db.get(Product, id)
    if data:
        db.delete(data)
        db.commit()
        return id
    else:
        raise HTTPException(detail=f"Product {id} not found!", status_code=status.HTTP_404_NOT_FOUND)


@app.get("/categories", response_model=List[CategoryGet])
def get_categories(db: db_annotation, params: url_params):
    fields = ["id", "name"]
    statement = select(Category)
    statement = UsefulAPI.all_in_one(statement,
                                    Category,
                                    params["filter"],
                                    params["sort"],
                                    fields,
                                    params["page"],
                                    params["limit"])
    data = db.exec(statement).all()
    return data

@app.get("/categories/used", response_model=List[CategoryGet])
def get_used_categories(db: db_annotation, p: url_params):
    fields = ["id", "name"]
    statement = select(Category).where(Category.id == Product.category_id).distinct()
    statement = UsefulAPI.all_in_one(statement, Category, p["filter"], p["sort"], fields, p["page"], p["limit"]).options(selectinload(Category.products))
    data = db.exec(statement).all()
    return data

@app.get("/categories/{id}", response_model=CategoryGet)
def get_category(db: db_annotation, id: int):
    data = db.get(Category, id)
    if data:
        return data
    raise HTTPException(detail=f"Category {id} not found!", status_code=status.HTTP_404_NOT_FOUND)

@app.put("/categories/{id}", response_model=CategoryGet)
def set_category(db: db_annotation, id: int, value: CategorySet, current_user: user_dep):
    if current_user.role.name != "admin":
        raise HTTPException(detail="Wrong role", status_code=status.HTTP_401_UNAUTHORIZED)
    data = db.get(Category, id)
    if data:
        for _k, _i in value.model_dump().items():
            if _i != None: setattr(data, _k, _i)
        db.add(data)
        db.commit()
        db.refresh(data)
        return data
    try:
        data = CategoryAdd(**value.model_dump())
        data = Category(**data.model_dump())
        db.add(data)
        db.commit()
        db.refresh(data)
        return data
    except ValidationError as e:
        db.rollback()
        raise HTTPException(detail=f"an error found with request, detail={e}", status_code=status.HTTP_422_UNPROCESSABLE_CONTENT)
    db.rollback()

@app.post("/categories", response_model=CategoryGet)
def add_category(db: db_annotation, value: CategoryAdd, current_user: user_dep):
    if current_user.role.name != "admin":
        raise HTTPException(detail="Wrong role", status_code=status.HTTP_401_UNAUTHORIZED)
    data = Category(**value.model_dump())
    db.add(data)
    db.commit()
    db.refresh(data)
    return data

@app.delete("/categories/{id}")
def delete_category(db: db_annotation, id: int, current_user: user_dep):
    if current_user.role.name != "admin":
        raise HTTPException(detail="Wrong role", status_code=status.HTTP_401_UNAUTHORIZED)
    data = db.get(Category, id)
    if data:
        db.delete(data)
        db.commit()
        return id
    raise HTTPException(detail=f"Category {id} not found", status_code=status.HTTP_404_NOT_FOUND)


@app.get("/users", response_model=List[UserGet])
def get_users(db: db_annotation, p: url_params):
    fields = ["id", "name", "role_id"]
    statement = select(User)
    statement = UsefulAPI.all_in_one(statement, User, p["filter"], p["sort"], fields, p["page"], p["limit"])
    data = db.exec(statement).all()
    return data

@app.get("/users/{id}", response_model=UserGet)
def get_user(db: db_annotation, id: int):
    data = db.get(User, id)
    if data:
        return data
    raise HTTPException(detail=f"User {id} not found!", status_code=status.HTTP_404_NOT_FOUND)

@app.post("/users", response_model=UserGet)
def add_user(db: db_annotation, value: UserAdd, current_user: user_dep):
    if current_user.role.name != "admin":
        raise HTTPException(detail="Wrong role", status_code=status.HTTP_401_UNAUTHORIZED)
    try:
        data = {**value.model_dump()}
        passwordandHash = bcrypt.hashpw(data["password_hash"].encode(), bcrypt.gensalt())
        data["password_hash"] = passwordandHash.decode()
        data = User(**data)
        db.add(data)
        db.commit()
        db.refresh(data)
        return data
    except ValidationError as e:
        raise HTTPException(detail=f"an error was occured detail:{e}", status_code=status.HTTP_422_UNPROCESSABLE_CONTENT)
    except IntegrityError as e:
        if isinstance(e.orig, UniqueViolation):
            db.rollback()
            raise HTTPException(detail="Error: name of user is repeating!", status_code=status.HTTP_422_UNPROCESSABLE_CONTENT)
    db.rollback()

@app.post("/token")
def checkPassword(db: db_annotation, value: Annotated[OAuth2PasswordRequestForm, Depends()]):
    names = value
    statement = select(User).where(User.name == names.username)
    data = db.exec(statement).first()
    if data:
        data = data.model_dump()
        token = create_token({"username": data["name"]})
        if bcrypt.checkpw(names.password.encode(), data["password_hash"].encode()):
            return {"access_token": token, "token_type": "bearer"}
    return False    

def create_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=45)
    to_encode["exp"] = expire
    encoded_jwt = jwt.encode(payload=to_encode, key=SECRET_KEY, algorithm="HS256")
    return encoded_jwt
