from typing import Optional
from fastapi import FastAPI, status, HTTPException
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

app = FastAPI()


URL_DATABASE = "mysql+pymysql://root:neversettle@db:3306/todoDB"


engine = create_engine(URL_DATABASE)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()



class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    description = Column(String(255), nullable=False)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))


Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

default_db = next(get_db())


class User(BaseModel):
    username: str

class UserCreate(User):
    password: str

class UserInDb(UserCreate):
    create_at: datetime
    update_at: datetime

class UserResponse(User):
    create_at: datetime
    update_at: datetime


class TaskRequest(BaseModel):
    title: str
    description: str

class TaskInDb(TaskRequest):
    id: int
    create_at: datetime
    update_at: datetime
    is_completed: bool

class TaskUpdate(BaseModel):
    id: int
    title: Optional[str] = None
    description: Optional[str] = None
    is_completed: Optional[bool] = None

def create_user(db, user: UserCreate):
    db_user = User(
        username=user.username,
        password=user.password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user_by_username(db, username: str):
    return db.query(User).filter(User.username == username).first()

def create_task(db, task: TaskRequest, user_id: int):
    db_task = Task(
        title=task.title,
        description=task.description,
        user_id=user_id
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def get_tasks_by_user(db, user_id: int):
    return db.query(Task).filter(Task.user_id == user_id).all()

def get_all_tasks(db):
    return db.query(Task).all()

def update_task(db, task_id: int, task_update: TaskUpdate):
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        return None
    if task_update.title is not None:
        db_task.title = task_update.title
    if task_update.description is not None:
        db_task.description = task_update.description
    if task_update.is_completed is not None:
        db_task.is_completed = task_update.is_completed
    db.commit()
    db.refresh(db_task)
    return db_task

def get_user(db, user_id: int):
    return db.query(User).filter(User.id == user_id).first()

def get_all_users(db):
    return db.query(User).all()

def check_user(db, user_id: int):
    return db.query(User).filter(User.id == user_id).first()

@app.get("/")
def index():
    return {
        "message": "Todo App"
    }

@app.post("/users", status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate):
    if not user.username  or not user.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All fields are required"
        )
    db_user = get_user_by_username(default_db, user.username)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already exists"
        )
    new_user = create_user(default_db, user)
    return {
        "success": True,
        "data": UserResponse(**new_user.__dict__),
        "message": "User created successfully"
    }

@app.get("/users")
def get_users():
    users = get_all_users(default_db)
    return {
        "success": True,
        "data": users,
        "message": "All Users retrived Successfully"
    }


@app.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_task_endpoint(task: TaskRequest, user_id:int):
    if not task.title or not task.description:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="All fields are required"
        )
    user = check_user(default_db, user_id)
    if not user:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail = "User does not exist"
        )
    new_task = create_task(default_db, task, user_id)
    return {
        "success": True,
        "data": new_task,
        "message": "Task created successfully"
    }

@app.get("/tasks")
def get_user_task(id:int):
    user = check_user(default_db, id)
    if not user:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail = "User does not exist"
        )
    user_task = get_tasks_by_user(default_db, id)
    return{
        "success": True,
        "data": user_task,
        "message": "All User task retrived successfully"
    }


@app.put("/tasks", status_code=status.HTTP_200_OK)
def update_task_endpoint(task_update: TaskUpdate):
    db_task = update_task(default_db, task_update.id, task_update)
    if not db_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    return {
        "success": True,
        "data": db_task,
        "message": "Task updated successfully"
    }