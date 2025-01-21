from fastapi import FastAPI, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from typing import Annotated
app = FastAPI()

engine = create_async_engine('sqlite+aiosqlite:///project.db')

new_session = async_sessionmaker(engine, expire_on_commit=False)

async def get_session():
    async with new_session() as session:
        yield session
SessionDep = Annotated[AsyncSession, Depends(get_session)]
class Base(DeclarativeBase):
    pass
class UserModel(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    user:Mapped[str]
    password:Mapped[str]


class Users(BaseModel):
    login: str
    password: str
   # login: str = Field(max_length=50, min_length=5),
   # password: str = Field(max_length=50, min_length=5)


@app.post(
    "/auth",
    tags=["Пользователи"])
async def add_user(data: Users, session: SessionDep):
    new_user = UserModel(
        user=data.login,
        password=data.password
    )
    session.add(new_user)
    await session.commit()
    return {"msg": "ok"}
@app.get(
    "/users",
    tags=["Пользователи"])
async def get_user():
    return {"msg": "ok"}

@app.post("/install")
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    return {"msg": "ok"}
@app.get("/")
def main():
    return "Hello World"