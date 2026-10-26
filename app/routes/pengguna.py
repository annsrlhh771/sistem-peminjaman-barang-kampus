from fastapi import APIRouter, HTTPException
from app.db import get_cursor

router = APIRouter()

@router.get("/")
def get_all_pengguna():
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT p.id_pengguna, p.nama_lengkap, p.nim_nip, p.email, p.no_telepon,
                   p.created_at, r.nama_peran
            FROM pengguna p JOIN peran r ON p.id_peran = r.id_peran
            ORDER BY p.id_pengguna
            """
        )
        rows = [dict(r) for r in cur.fetchall()]
    return {"message": "Daftar pengguna", "data": rows}

@router.get("/{id_pengguna}")
def get_pengguna(id_pengguna: int):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT p.id_pengguna, p.nama_lengkap, p.nim_nip, p.email, p.no_telepon,
                   p.created_at, r.nama_peran
            FROM pengguna p JOIN peran r ON p.id_peran = r.id_peran
            WHERE p.id_pengguna=%s
            """,
            (id_pengguna,),
        )
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Pengguna tidak ditemukan")
    return {"data": dict(row)}