from typing import Annotated
from authx import AuthXConfig, AuthX
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
#############################модели валидации###################################

class Users_Model(BaseModel):
    login: str = Field(min_length=6, max_length=30)
    password: str = Field(min_length=6, max_length=30)
@app.post('/create_db',tags=["База данных"])     #создание таблицы
async def create_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all) #по умолчанию create_all не создает существующие таблицы
    return {"ok": True}
@app.post('/add_account',tags=["База данных"]) #создание аккаунта
async def add_account(data: Users_Model, session: AsyncSession = Depends(get_db)):
    new_account = accounts_db(login=data.login, password=data.password)
    session.add(new_account)
    await session.commit()
    return {"msg": True}


@app.post("/auth")
async def login(data: Users_Model,session : AsyncSession = Depends(get_db)): #роут для авторизации
    req = select(accounts_db).where(accounts_db.login == data.login and accounts_db.password == data.password )
    result = await session.execute(req)
    if result is not None:
        row = result.scalars().first()
        token = auth.create_access_token(uid=str(row.id))
        return {"id":row.id,"login":row.login,"token": token}
    else:
        raise HTTPException(401, detail="invalid credentials")
    await session.commit()









@app.get("/")
def main():
    return "Hello World"