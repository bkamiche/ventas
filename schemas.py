from pydantic import BaseModel

class LoginRequest(BaseModel):
    usuario: str
    contrasena: str

class Token(BaseModel):
    access_token: str
    token_type: str