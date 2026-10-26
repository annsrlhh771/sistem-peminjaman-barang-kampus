from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db import get_cursor

router = APIRouter()

class KategoriBody(BaseModel):
    nama_kategori: str
    deskripsi: str | None = None

@router.get("/")
def get_kategori():
    with get_cursor() as cur:
        cur.execute("SELECT * FROM kategori_barang ORDER BY id_kategori")
        rows = [dict(r) for r in cur.fetchall()]
    return {"message": "Daftar kategori", "data": rows}

@router.post("/", status_code=201)
def create_kategori(body: KategoriBody):
    if not body.nama_kategori.strip():
        raise HTTPException(status_code=400, detail="nama_kategori wajib diisi")

    with get_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO kategori_barang (nama_kategori, deskripsi) VALUES (%s,%s) RETURNING *",
            (body.nama_kategori, body.deskripsi),
        )
        row = dict(cur.fetchone())

    return {"message": "Kategori berhasil ditambahkan", "data": row}