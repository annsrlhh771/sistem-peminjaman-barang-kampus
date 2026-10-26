from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from app.db import get_connection
from psycopg2.extras import RealDictCursor

router = APIRouter()

class PeminjamanBody(BaseModel):
    id_pengguna: int
    tanggal_pinjam: date
    tanggal_kembali_rencana: date
    keperluan: str
    id_barang: List[int]

class SetujuiBody(BaseModel):
    id_admin: int
    catatan_admin: Optional[str] = None

class TolakBody(BaseModel):
    id_admin: int
    catatan_admin: str

@router.post("/", status_code=201)
def ajukan_peminjaman(body: PeminjamanBody):
    if not body.id_barang:
        raise HTTPException(status_code=400, detail="id_barang minimal 1")
    if body.tanggal_kembali_rencana < body.tanggal_pinjam:
        raise HTTPException(status_code=400, detail="tanggal_kembali_rencana tidak boleh sebelum tanggal_pinjam")

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("BEGIN")

        cur.execute(
            "SELECT id_barang, nama_barang, status FROM barang WHERE id_barang = ANY(%s)",
            (body.id_barang,),
        )
        rows = [dict(r) for r in cur.fetchall()]

        if len(rows) != len(body.id_barang):
            cur.execute("ROLLBACK")
            raise HTTPException(status_code=400, detail="Ada barang yang tidak ditemukan")

        tidak_tersedia = [r for r in rows if r["status"] != "tersedia"]
        if tidak_tersedia:
            cur.execute("ROLLBACK")
            raise HTTPException(status_code=400, detail={"message": "Beberapa barang tidak tersedia", "detail": tidak_tersedia})

        cur.execute(
            """
            INSERT INTO peminjaman (id_pengguna, tanggal_pinjam, tanggal_kembali_rencana, keperluan)
            VALUES (%s,%s,%s,%s) RETURNING *
            """,
            (body.id_pengguna, body.tanggal_pinjam, body.tanggal_kembali_rencana, body.keperluan),
        )
        pinjam = dict(cur.fetchone())
        id_peminjaman = pinjam["id_peminjaman"]

        for idb in body.id_barang:
            cur.execute(
                "INSERT INTO detail_peminjaman (id_peminjaman, id_barang) VALUES (%s,%s)",
                (id_peminjaman, idb),
            )

        conn.commit()
        cur.close()
        pinjam["id_barang"] = body.id_barang
        return {"message": "Pengajuan peminjaman berhasil", "data": pinjam}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.get("/")
def get_peminjaman(status: Optional[str] = Query(None)):
    sql = """
        SELECT p.*, u.nama_lengkap AS peminjam,
          COALESCE(json_agg(json_build_object(
            'id_barang', b.id_barang,
            'nama_barang', b.nama_barang,
            'kode_barang', b.kode_barang
          )) FILTER (WHERE b.id_barang IS NOT NULL), '[]') AS barang
        FROM peminjaman p
        JOIN pengguna u ON p.id_pengguna = u.id_pengguna
        LEFT JOIN detail_peminjaman dp ON p.id_peminjaman = dp.id_peminjaman
        LEFT JOIN barang b ON dp.id_barang = b.id_barang
        WHERE 1=1
    """
    params = []
    if status:
        sql += " AND p.status = %s"
        params.append(status)
    sql += " GROUP BY p.id_peminjaman, u.nama_lengkap ORDER BY p.id_peminjaman DESC"

    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()

    return {"message": "Daftar peminjaman", "data": rows}

@router.get("/riwayat/{id_pengguna}")
def get_riwayat(id_pengguna: int):
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            SELECT p.*, COALESCE(json_agg(json_build_object(
                'id_barang', b.id_barang, 'nama_barang', b.nama_barang,
                'sudah_dikembalikan', pg.id_pengembalian IS NOT NULL
              )) FILTER (WHERE b.id_barang IS NOT NULL), '[]') AS barang
            FROM peminjaman p
            LEFT JOIN detail_peminjaman dp ON p.id_peminjaman = dp.id_peminjaman
            LEFT JOIN barang b ON dp.id_barang = b.id_barang
            LEFT JOIN pengembalian pg ON dp.id_detail = pg.id_detail
            WHERE p.id_pengguna = %s
            GROUP BY p.id_peminjaman ORDER BY p.tanggal_pengajuan DESC
            """,
            (id_pengguna,),
        )
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()

    return {"message": "Riwayat peminjaman", "data": rows}

@router.get("/{id_peminjaman}")
def get_peminjaman_by_id(id_peminjaman: int):
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            SELECT p.*, u.nama_lengkap AS peminjam
            FROM peminjaman p JOIN pengguna u ON p.id_pengguna = u.id_pengguna
            WHERE p.id_peminjaman=%s
            """,
            (id_peminjaman,),
        )
        row = cur.fetchone()
        if not row:
            cur.close()
            raise HTTPException(status_code=404, detail="Peminjaman tidak ditemukan")

        cur.execute(
            """
            SELECT dp.id_detail, b.id_barang, b.nama_barang, b.kode_barang, pg.id_pengembalian
            FROM detail_peminjaman dp
            JOIN barang b ON dp.id_barang = b.id_barang
            LEFT JOIN pengembalian pg ON dp.id_detail = pg.id_detail
            WHERE dp.id_peminjaman=%s
            """,
            (id_peminjaman,),
        )
        detail = [dict(r) for r in cur.fetchall()]
        cur.close()

    result = dict(row)
    result["detail"] = detail
    return {"data": result}

@router.patch("/{id_peminjaman}/setujui")
def setujui_peminjaman(id_peminjaman: int, body: SetujuiBody):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("BEGIN")
        cur.execute(
            "SELECT * FROM peminjaman WHERE id_peminjaman=%s FOR UPDATE",
            (id_peminjaman,),
        )
        pinjam = cur.fetchone()
        if not pinjam:
            cur.execute("ROLLBACK")
            raise HTTPException(status_code=404, detail="Peminjaman tidak ditemukan")

        if pinjam["status"] != "diajukan":
            cur.execute("ROLLBACK")
            raise HTTPException(
                status_code=400,
                detail=f"Hanya peminjaman berstatus 'diajukan' yang bisa disetujui (sekarang: {pinjam['status']})",
            )

        cur.execute(
            """UPDATE peminjaman SET status='disetujui', id_admin=%s, catatan_admin=%s,
               tanggal_diproses=NOW() WHERE id_peminjaman=%s""",
            (body.id_admin, body.catatan_admin, id_peminjaman),
        )
        cur.execute(
            """UPDATE barang SET status='dipinjam'
               WHERE id_barang IN (SELECT id_barang FROM detail_peminjaman WHERE id_peminjaman=%s)""",
            (id_peminjaman,),
        )
        conn.commit()
        cur.close()
        return {"message": "Peminjaman disetujui"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.patch("/{id_peminjaman}/tolak")
def tolak_peminjaman(id_peminjaman: int, body: TolakBody):
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT status FROM peminjaman WHERE id_peminjaman=%s", (id_peminjaman,))
        row = cur.fetchone()
        if not row:
            cur.close()
            raise HTTPException(status_code=404, detail="Peminjaman tidak ditemukan")
        if row["status"] != "diajukan":
            cur.close()
            raise HTTPException(
                status_code=400,
                detail=f"Hanya peminjaman berstatus 'diajukan' yang bisa ditolak (sekarang: {row['status']})",
            )

        cur.execute(
            """UPDATE peminjaman SET status='ditolak', id_admin=%s, catatan_admin=%s,
               tanggal_diproses=NOW() WHERE id_peminjaman=%s""",
            (body.id_admin, body.catatan_admin, id_peminjaman),
        )
        conn.commit()
        cur.close()

    return {"message": "Peminjaman ditolak"}