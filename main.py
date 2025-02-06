import shutil
import traceback
from datetime import timedelta, date
from typing import Annotated
import uvicorn
import os
from nanoid import generate
from passlib.context import CryptContext
from authx import AuthXConfig, AuthX, RequestToken, TokenPayload
from fastapi import FastAPI, Depends, HTTPException, UploadFile,File
from pydantic import BaseModel, Field, FilePath
from sqlalchemy import create_engine, Column, select, ForeignKey, Integer, delete, LargeBinary,Date
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
app = FastAPI()
#############################конфигурация авторизации###################################
config = AuthXConfig(
    JWT_ALGORITHM="HS256",
    JWT_SECRET_KEY="SecretKey",
    JWT_TOKEN_LOCATION=['json'],
    JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=15),
    JWT_REFRESH_TOKEN_EXPIRES=timedelta(days=7)
)
authZ = AuthX(config)
authZ.handle_errors(app)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
#############################база данных###################################
engine = create_async_engine('postgresql+asyncpg://jesus:kotakpass@84.19.3.28/fastapijesus') #тип бд+движок://логин:пасс@host/db
new_session = async_sessionmaker(engine) # создание асинхсессии
async def get_db():
    async with new_session() as session:
        yield session #ожидание выполнение сессии

class Base(DeclarativeBase):
    pass
class accounts_db(Base):
    __tablename__ = 'accounts' #название таблицы
    __table_args__ = {'schema': 'kotakbus'}
    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str]
    password: Mapped[str]

class profiles_db(Base):
    __tablename__ = 'profiles'
    __table_args__ = {'schema': 'kotakbus'}
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str]
    password: Mapped[str]
   # account_id: Mapped[int] = mapped_column(foreign_key=accounts_db.id)
   #  account_id = Column(Integer, ForeignKey('accounts.id'))
    account_id = Column(Integer)
class desc_profiles_db(Base):
    __tablename__ = 'desc_profiles'
    __table_args__ = {'schema': 'kotakbus'}
    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str]
    last_name: Mapped[str]
    birth_date = Column(Date)
    avatar: Mapped[str]
    # profile_id = Column(Integer, ForeignKey('profiles.id'))
    profile_id = Column(Integer)
#############################модели валидации###################################

class Users_Model(BaseModel):
    login: str = Field(min_length=6, max_length=30)
    password: str = Field(min_length=6, max_length=30)
class Profiles_Model(BaseModel):
    username: str = Field(min_length=6, max_length=30)
    password: str = Field(min_length=6, max_length=30)
class Profiles_desc(BaseModel):
    first_name: str = Field(min_length=2, max_length=300)
    last_name: str = Field(min_length=2, max_length=300)
    birth_date: date
    # avatar: FilePath

@app.post('/create_db',tags=["База данных"])     #создание таблицы
async def create_db():
    # try:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all) #по умолчанию create_all не создает существующие таблицы
    return {"ok": True}
    # except Exception as e:
    #    print( {"msg": str(e)})
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

@app.post("/authorization")
async def login(data: Users_Model,session : AsyncSession = Depends(get_db)): #роут для авторизации
   # req = select(accounts_db).where(accounts_db.login == data.login and accounts_db.password == data.password )
    req = select(accounts_db).where(accounts_db.login == data.login)
    result = await session.execute(req)
    row = result.scalars().first()
    if row is not None:
        pass_bool = verify_password(data.password, str(row.password))
        if pass_bool:
            access_token = authZ.create_access_token(uid=str(row.id),fresh=True)
            refresh_token = authZ.create_refresh_token(uid=str(row.id))
            return {"id":row.id,"login":row.login,"access_token": access_token,"refresh_token":refresh_token}
        else:
            return {"msg":"Неправильный логин или пароль"}
    else:
        raise HTTPException(401, detail="invalid credentials")
   # await session.commit()
@app.delete("/account/del_account")
async def delete_account( tk : TokenPayload  = Depends(authZ.access_token_required),
                         session: AsyncSession = Depends(get_db)):
    try:
        res = await session.execute(select(accounts_db).where(accounts_db.id == int(tk.sub)))
        find_acc = res.scalars().first()
        await session.delete(find_acc)
        await session.commit()
        return {"msg":True}
    except Exception as e:
        print(str(e), traceback.format_exc())
        return {"msg":str(e)}


@app.post("/logout") #ДОБАВИТЬ ОТЗЫВ РЕФРЕШ ТОКЕНА
def logout(token: RequestToken = Depends(authZ.access_token_required)):
    token.revoke_token(token)
    return {"ok": True}
@app.post("/refresh")
def refresh(token: TokenPayload = Depends(authZ.refresh_token_required)):
    access_token = authZ.create_access_token(token.sub)
    return {"access_token": access_token}
#########################Необходимо разбирать на роуты#####################################



#########################       ПРОФИЛИ    #####################################
@app.post("/account/create_profile")
async def create_profile(data: Profiles_Model, session: AsyncSession = Depends(get_db), tk : TokenPayload  = Depends(authZ.access_token_required)):
    try:
        res = await session.execute(select(profiles_db).filter(profiles_db.username == data.username))
        if res.scalars().first() is None:
            hash_pass = get_password_hash(data.password)
            session.add(profiles_db(username=data.username,password=hash_pass,account_id=int(tk.sub)))
            await session.commit()
            return {"create_profile": True}
        else:
            return {"create_profile":False}
    except Exception as e:
        return {"create_profile":False,"error":str(e)}


@app.get("/account/get_profiles")
async def get_profiles( session: AsyncSession = Depends(get_db), tk : TokenPayload  = Depends(authZ.access_token_required)):
    try:
        res = await session.execute(select(profiles_db).filter(profiles_db.account_id == int(tk.sub)))
        prof = res.mappings().all()
        # if res.scalars().first() is None:
        #     return {"Count_profiles": False}
        # else:
        return prof
    except Exception as e:
        return {"Count_profiles":False,"error":str(e)}

@app.get("/account/profile/{profile_id}/desc_profile", dependencies=[Depends(authZ.get_token_from_request)])
async def get_profile(profile_id: str, session: AsyncSession = Depends(get_db), token: RequestToken = Depends()):
    try:
        vt = authZ.verify_token(token=token)
        res = await session.execute(select(desc_profiles_db).filter(desc_profiles_db.profile_id == int(profile_id)))
        if res.scalars().first() is None:
            return {"desc_profiles": False}
        else:
            return res.scalars()
    except Exception as e:
        return {"error":str(e)}


@app.post("/account/profile/desc_profile_save", tags=["Работа с профилями"])
async def save_profile(data: Profiles_desc, session: AsyncSession = Depends(get_db),
                       file: UploadFile = File(...)):
    try:
        new_name = generate(file.filename, 21)
        file_path = os.path.join(UPLOAD_DIR, new_name)
        with open(file_path,"wb") as buff:
            shutil.copyfile(file.filename, file_path )
        # session.add(desc_profiles_db(first_name = data.first_name,last_name=data.last_name,birth_date=data.birth_date,avatar=file_path))
        # await session.commit()
    except Exception as e:
        return {"error":str(e)}

@app.get("/profile_view", dependencies=[Depends(authZ.get_token_from_request)]) #протектед роут
def profile_view(token: RequestToken = Depends()):
    try:
        authZ.verify_token(token=token)
        return {"msg_access":True}
    except:
        raise HTTPException(401, detail="invalid credentials")



@app.get("/")
def main():
    return "Hello World"
#if __name__ == "__main__":
 #   uvicorn.run("main:app", port=5000, log_level="info")