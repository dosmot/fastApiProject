from fastapi import FastAPI, HTTPException, Response
from authx import AuthX, AuthXConfig
from fastapi.params import Depends
from pydantic import BaseModel
# описание кода
app = FastAPI()

config = AuthXConfig() # объект для работы построения конфигурации
config.JWT_SECRET_KEY = "SECRET_KEY" # задается секретный ключ для работы с куками/заголовками
config.JWT_ACCESS_COOKIE_NAME = "my_access_token" # имя доступа в данном случае куки
config.JWT_TOKEN_LOCATION = ["cookies"] # в чем хранится токен, в данном случае куки, может заголовки. Заголовки для универсального приложения

security = AuthX(config= config) # создается объект механизма авторизации с настроенным конфигом выше

class UserItem(BaseModel):  # модель для валидации данных используемых для авторизации
    username: str
    password: str

@app.post("/login")
def login(user: UserItem, response: Response): # user - это данные валидации с которыми будем работать. response -  это объект фаст апи, для работы с ответами, в данном случае
    # устанавливается/передаются куки(имя, сам токен)
    if user.username =="" and user.password == "":
        token = security.create_access_token(uid="1") # создается токен в котором будет лежать номер айди при подтверждении авторизации
        response.set_cookie("my_access_token", token)
        return token
    raise HTTPException(status_code=401, detail="Username or password is incorrect")

@app.get("/enter", dependencies=[Depends(security.access_token_required)]) # depends - говорит о том что необходимо вызвать функци из security и получить её результат
def protected():
    return {"message": "Hello"}

