from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.db import get_connection
from psycopg2.extras import RealDictCursor

router = APIRouter()

class PengembalianBody(BaseModel):
    id_detail: int
    id_admin: Optional[int] = None
    kondisi: Optional[str] = "baik"
    catatan: Optional[str] = None

@router.post("/", status_code=201)
def proses_pengembalian(body: PengembalianBody):
    allowed = ["baik", "rusak_ringan", "rusak_berat", "hilang"]
    if body.kondisi not in allowed:
        raise HTTPException(status_code=400, detail=f"kondisi harus salah satu dari: {', '.join(allowed)}")

    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("BEGIN")

        cur.execute(
            """
            SELECT dp.*, p.id_peminjaman, p.status AS status_peminjaman
            FROM detail_peminjaman dp
            JOIN peminjaman p ON dp.id_peminjaman = p.id_peminjaman
            WHERE dp.id_detail = %s
            """,
            (body.id_detail,),
        )
        detail = cur.fetchone()
        if not detail:
            cur.execute("ROLLBACK")
            raise HTTPException(status_code=404, detail="Detail peminjaman tidak ditemukan")

        if detail["status_peminjaman"] not in ("disetujui", "dipinjam"):
            cur.execute("ROLLBACK")
            raise HTTPException(status_code=400, detail="Peminjaman belum disetujui atau sudah selesai")

        cur.execute("SELECT 1 FROM pengembalian WHERE id_detail=%s", (body.id_detail,))
        if cur.fetchone():
            cur.execute("ROLLBACK")
            raise HTTPException(status_code=400, detail="Barang pada detail ini sudah dikembalikan")

        cur.execute(
            """INSERT INTO pengembalian (id_detail, id_admin, kondisi, catatan)
               VALUES (%s,%s,%s,%s) RETURNING *""",
            (body.id_detail, body.id_admin, body.kondisi, body.catatan),
        )
        result = dict(cur.fetchone())

        status_baru = "tersedia" if body.kondisi == "baik" else "perbaikan"
        cur.execute(
            """UPDATE barang SET status=%s
               WHERE id_barang = (SELECT id_barang FROM detail_peminjaman WHERE id_detail=%s)""",
            (status_baru, body.id_detail),
        )

        cur.execute(
            """SELECT COUNT(*) AS sisa FROM detail_peminjaman dp
               LEFT JOIN pengembalian pg ON dp.id_detail = pg.id_detail
               WHERE dp.id_peminjaman = %s AND pg.id_pengembalian IS NULL""",
            (detail["id_peminjaman"],),
        )
        sisa = cur.fetchone()["sisa"]
        if sisa == 0:
            cur.execute(
                "UPDATE peminjaman SET status='selesai' WHERE id_peminjaman=%s",
                (detail["id_peminjaman"],),
            )

        conn.commit()
        cur.close()
        return {"message": "Pengembalian berhasil dicatat", "data": result}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()