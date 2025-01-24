from typing import Annotated
from passlib.context import CryptContext
from authx import AuthXConfig, AuthX, RequestToken, TokenPayload
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column,select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
app = FastAPI()
#############################конфигурация авторизации###################################
config = AuthXConfig(
    JWT_ALGORITHM="HS256",
    JWT_SECRET_KEY="SecretKey",
    JWT_TOKEN_LOCATION=['json']
)
auth = AuthX(config)
auth.handle_errors(app)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
#############################база данных###################################
engine = create_async_engine('postgresql+asyncpg://postgres:123@localhost/Project_test') #тип бд+движок://логин:пасс@host/db
new_session = async_sessionmaker(engine) # создание асинхсессии
async def get_db():
    async with new_session() as session:
        yield session #ожидание выполнение сессии

class Base(DeclarativeBase):
    pass
class accounts_db(Base):
    __tablename__ = 'accounts' #название таблицы
    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str]
    password: Mapped[str]

class profiles_db(Base):
    __tablename__ = 'profiles'
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str]
    password: Mapped[str]
    account_id: Mapped[int] = mapped_column(foreign_key=accounts_db.id)

class desc_profiles_db(Base):
    __tablename__ = 'desc_profiles'
    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str]
    last_name: Mapped[str]
    birth_date: Mapped[str]
    avatar: Mapped[str]
    profile_id: Mapped[int] = mapped_column(foreign_key=profiles_db.id)
#############################модели валидации###################################

class Users_Model(BaseModel):
    login: str = Field(min_length=6, max_length=30)
    password: str = Field(min_length=6, max_length=30)
#class Profiles_Model(BaseModel):

@app.post('/create_db',tags=["База данных"])     #создание таблицы
async def create_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all) #по умолчанию create_all не создает существующие таблицы
    return {"ok": True}
@app.post('/add_account',tags=["База данных"]) #создание аккаунта
async def add_account(data: Users_Model, session: AsyncSession = Depends(get_db)):
    try:
        res = await session.execute(select(accounts_db).filter(accounts_db.login == data.login))
        exist_user = res.scalars().first()
        if exist_user:
            raise HTTPException(400, detail="Пользователь уже существует")
        hash_pass = get_password_hash(data.password)
        new_account = accounts_db(login=data.login, password=hash_pass)
        session.add(new_account)
        await session.commit()
        return {"msg": True}
    except:
        await session.rollback()
        raise HTTPException(400, detail="Пользователь уже существует")

@app.post("/auth")
async def login(data: Users_Model,session : AsyncSession = Depends(get_db)): #роут для авторизации
   # req = select(accounts_db).where(accounts_db.login == data.login and accounts_db.password == data.password )
    req = select(accounts_db).where(accounts_db.login == data.login)
    result = await session.execute(req)
    if result is not None:
        row = result.scalars().first()
        pass_bool = verify_password(data.password, str(row.password))
        if pass_bool:
            access_token = auth.create_access_token(uid=str(row.id),fresh=True)
            refresh_token = auth.create_refresh_token(uid=str(row.id))
            return {"id":row.id,"login":row.login,"access_token": access_token,"refresh_token":refresh_token}
        else:
            return {"msg":"Неправильный логин или пароль"}
    else:
        raise HTTPException(401, detail="invalid credentials")
   # await session.commit()
@app.post("/logout") #ДОБАВИТЬ ОТЗЫВ РЕФРЕШ ТОКЕНА
def logout(token: RequestToken = Depends(auth.access_token_required)):
    token.revoke_token(token)
    return {"ok": True}
@app.post("/refresh")
def refresh(token: TokenPayload = Depends(auth.refresh_token_required)):
    access_token = auth.create_access_token(token.sub)
    return {"access_token": access_token}
#########################Необходимо разбирать на роуты#####################################
@app.get("/profile_view", dependencies=[Depends(auth.get_token_from_request)]) #протектед роут
def profile_view(token: RequestToken = Depends()):
    try:
        auth.verify_token(token=token)
        return {"msg_access":True}
    except:
        raise HTTPException(401, detail="invalid credentials")



@app.get("/")
def main():
    return "Hello World"