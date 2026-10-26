from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from app.db import get_cursor

router = APIRouter()

class BarangBody(BaseModel):
    id_kategori: int
    kode_barang: str
    nama_barang: str
    deskripsi: Optional[str] = None
    lokasi_simpan: Optional[str] = None

class StatusBody(BaseModel):
    status: str

@router.get("/")
def get_barang(
    status: Optional[str] = Query(None),
    id_kategori: Optional[int] = Query(None),
):
    sql = """
        SELECT b.*, k.nama_kategori
        FROM barang b JOIN kategori_barang k ON b.id_kategori = k.id_kategori
        WHERE 1=1
    """
    params = []
    if status:
        sql += " AND b.status = %s"
        params.append(status)
    if id_kategori:
        sql += " AND b.id_kategori = %s"
        params.append(id_kategori)
    sql += " ORDER BY b.id_barang"

    with get_cursor() as cur:
        cur.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]
    return {"message": "Daftar barang", "total": len(rows), "data": rows}

@router.get("/{id_barang}")
def get_barang_by_id(id_barang: int):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT b.*, k.nama_kategori FROM barang b
            JOIN kategori_barang k ON b.id_kategori = k.id_kategori
            WHERE b.id_barang = %s
            """,
            (id_barang,),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Barang tidak ditemukan")
    return {"data": dict(row)}

@router.get("/{id_barang}/ketersediaan")
def cek_ketersediaan(id_barang: int):
    with get_cursor() as cur:
        cur.execute(
            "SELECT id_barang, nama_barang, status FROM barang WHERE id_barang=%s",
            (id_barang,),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Barang tidak ditemukan")

    return {
        "id_barang": row["id_barang"],
        "nama_barang": row["nama_barang"],
        "tersedia": row["status"] == "tersedia",
        "status": row["status"],
    }

@router.post("/", status_code=201)
def create_barang(body: BarangBody):
    if not body.kode_barang or not body.nama_barang:
        raise HTTPException(status_code=400, detail="kode_barang, nama_barang wajib diisi")

    try:
        with get_cursor(commit=True) as cur:
            cur.execute(
                """
                INSERT INTO barang (id_kategori, kode_barang, nama_barang, deskripsi, lokasi_simpan)
                VALUES (%s,%s,%s,%s,%s) RETURNING *
                """,
                (body.id_kategori, body.kode_barang, body.nama_barang, body.deskripsi, body.lokasi_simpan),
            )
            row = dict(cur.fetchone())
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=400, detail="kode_barang sudah dipakai")
        raise HTTPException(status_code=400, detail=str(e))

    return {"message": "Barang berhasil ditambahkan", "data": row}

@router.put("/{id_barang}")
def update_barang(id_barang: int, body: BarangBody):
    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            UPDATE barang SET id_kategori=%s, kode_barang=%s, nama_barang=%s,
                   deskripsi=%s, lokasi_simpan=%s
            WHERE id_barang=%s RETURNING *
            """,
            (body.id_kategori, body.kode_barang, body.nama_barang, body.deskripsi, body.lokasi_simpan, id_barang),
        )
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Barang tidak ditemukan")
    return {"message": "Barang berhasil diupdate", "data": dict(row)}

@router.patch("/{id_barang}/status")
def update_status(id_barang: int, body: StatusBody):
    allowed = ["tersedia", "dipinjam", "perbaikan"]
    if body.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"status harus salah satu dari: {', '.join(allowed)}",
        )

    with get_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE barang SET status=%s WHERE id_barang=%s RETURNING *",
            (body.status, id_barang),
        )
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Barang tidak ditemukan")
    return {"message": "Status barang diperbarui", "data": dict(row)}

@router.delete("/{id_barang}")
def delete_barang(id_barang: int):
    try:
        with get_cursor(commit=True) as cur:
            cur.execute("DELETE FROM barang WHERE id_barang=%s RETURNING *", (id_barang,))
            row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Barang tidak ditemukan")
        return {"message": "Barang berhasil dihapus", "data": dict(row)}
    except HTTPException:
        raise
    except Exception as e:
        if "foreign key" in str(e).lower():
            raise HTTPException(status_code=400, detail="Barang tidak bisa dihapus karena masih terkait peminjaman")
        raise HTTPException(status_code=500, detail=str(e))