from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db import get_connection
from psycopg2.extras import RealDictCursor

router = APIRouter()

class KategoriBody(BaseModel):
    nama_kategori: str
    deskripsi: str | None = None

@router.get("/")
def get_kategori():
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM kategori_barang ORDER BY id_kategori")
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()
        conn.close()
        return {"message": "Daftar kategori", "data": rows}
    except Exception as e:
        print("ERROR KATEGORI:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", status_code=201)
def create_kategori(body: KategoriBody):
    if not body.nama_kategori.strip():
        raise HTTPException(status_code=400, detail="nama_kategori wajib diisi")

    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            "INSERT INTO kategori_barang (nama_kategori, deskripsi) VALUES (%s,%s) RETURNING *",
            (body.nama_kategori, body.deskripsi),
        )
        conn.commit()
        row = dict(cur.fetchone())
        cur.close()
        conn.close()
        return {"message": "Kategori berhasil ditambahkan", "data": row}
    except Exception as e:
        print("ERROR KATEGORI:", str(e))
        raise HTTPException(status_code=500, detail=str(e))