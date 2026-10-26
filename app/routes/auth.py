from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from app.db import get_cursor
from app.auth_utils import hash_password, verify_password, create_token

router = APIRouter()

class RegisterBody(BaseModel):
    id_peran: int
    nama_lengkap: str
    nim_nip: str
    email: str
    password: str
    no_telepon: str | None = None

class LoginBody(BaseModel):
    email: str
    password: str

@router.post("/register", status_code=201)
def register(body: RegisterBody):
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password minimal 6 karakter")

    with get_cursor(commit=False) as cur:
        cur.execute(
            "SELECT 1 FROM pengguna WHERE email=%s OR nim_nip=%s",
            (body.email, body.nim_nip),
        )
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Email atau NIM/NIP sudah terdaftar")

    hashed = hash_password(body.password)

    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO pengguna (id_peran, nama_lengkap, nim_nip, email, password_hash, no_telepon)
            VALUES (%s,%s,%s,%s,%s,%s)
            RETURNING id_pengguna, id_peran, nama_lengkap, nim_nip, email, no_telepon, created_at
            """,
            (body.id_peran, body.nama_lengkap, body.nim_nip, body.email, hashed, body.no_telepon),
        )
        user = dict(cur.fetchone())

    return {"message": "Registrasi berhasil", "data": user}

@router.post("/login")
def login(body: LoginBody):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT p.*, r.nama_peran
            FROM pengguna p JOIN peran r ON p.id_peran = r.id_peran
            WHERE p.email=%s
            """,
            (body.email,),
        )
        user = cur.fetchone()

    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email atau password salah")

    token = create_token({
        "id_pengguna": user["id_pengguna"],
        "id_peran": user["id_peran"],
        "nama_peran": user["nama_peran"],
    })

    return {
        "message": "Login berhasil",
        "token": token,
        "data": {
            "id_pengguna": user["id_pengguna"],
            "nama_lengkap": user["nama_lengkap"],
            "email": user["email"],
            "nama_peran": user["nama_peran"],
        },
    }