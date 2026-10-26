from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routes import auth, pengguna, kategori, barang, peminjaman, pengembalian

app = FastAPI(
    title="Sistem Peminjaman Barang Kampus API",
    version="1.0.0",
    description="REST API Sistem Peminjaman Barang Kampus — FastAPI + Supabase PostgreSQL",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "name": "Sistem Peminjaman Barang Kampus API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": [
            "POST   /auth/register",
            "POST   /auth/login",
            "GET    /pengguna",
            "GET    /pengguna/{id}",
            "GET    /kategori",
            "POST   /kategori",
            "GET    /barang",
            "GET    /barang/{id}",
            "GET    /barang/{id}/ketersediaan",
            "POST   /barang",
            "PUT    /barang/{id}",
            "PATCH  /barang/{id}/status",
            "DELETE /barang/{id}",
            "POST   /peminjaman",
            "GET    /peminjaman",
            "GET    /peminjaman/riwayat/{id_pengguna}",
            "GET    /peminjaman/{id}",
            "PATCH  /peminjaman/{id}/setujui",
            "PATCH  /peminjaman/{id}/tolak",
            "POST   /pengembalian",
        ],
    }

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(pengguna.router, prefix="/pengguna", tags=["Pengguna"])
app.include_router(kategori.router, prefix="/kategori", tags=["Kategori"])
app.include_router(barang.router, prefix="/barang", tags=["Barang"])
app.include_router(peminjaman.router, prefix="/peminjaman", tags=["Peminjaman"])
app.include_router(pengembalian.router, prefix="/pengembalian", tags=["Pengembalian"])