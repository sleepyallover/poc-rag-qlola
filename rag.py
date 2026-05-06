from openai import OpenAI
import psycopg2
from sqlalchemy import create_engine
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()  # This loads the variables from .env into the environment
api_key = os.getenv("OPENAI_API_KEY")
supabase_url = os.getenv("SUPABASE_DB_URL")

client=OpenAI(api_key=api_key)
engine = create_engine(supabase_url)

SCHEMA = """
Tables:

master_qlola(ds : posisi data dalam format YYYYmm, 
acctno : nomor rekening,
jenis_simpanan: GIRO atau BRITAMA BISNIS,
open_date: tanggal pembukaan rekening,
cifno: CIF nasabah (unique),
flag_qlola_cif: flag apakah suatu cif memiliki qlola,
ro: regional office atau kanwil,
segmen: segmentasi berdasarkan acctno (KORPORASI, SME, MIKRO, KONSUMER),
segmentasi_cif: segmentasi berdasarkan cif (KORPORASI, SME, MIKRO, KONSUMER),
group_pengelola: group pengelola rekening,
status: active atau inactive,
endbal: saldo atau balance atau CASA,
ratas_saldo: rerata saldo atau balance atau CASA,
featuredesc: fitur transaksi qlola yang digunakan (BI FAST, RTGS, KLIRING, FUND TRANSFER),
kode_cabang: kode kantor cabang rumah nomor rekening,
nama_cabang: nama kantor cabang rumah nomor rekening,
freq_qlola: frekuensi transaksi menggunakan qlola,
sv_qlola: nominal sales volume transaksi menggunakan qlola,
fbi_qlola: jumlah fbi transaksi qlola)

transaction_non_qlola(ds  : posisi data dalam format YYYYmm,
acctno: nomor rekening,
jenis_trx: jenis transaksi yang dilakukan (BI FAST, RTGS, KLIRING, FUND TRANSFER),
freq_trx: frekuensi transaksi non qlola,
sv_trx: nominal sales volume transaksi non qlola)
"""

def generate_sql(question):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": f"""Kamu adalah seorang data analis. Tugasmu adalah melakukan running SQL sesuai pertanyaan user.
                Rules:
                - Hanya gunakan table berdasarkan SCHEMA yang ada
                - Hanya generate query SELECT 
                - Always include LIMIT 100
                - Never use SELECT *
                - Untuk segmentasi, utamakan segmentasi_cif kecuali user menyatakan sebaliknya

                SCHEMA= {SCHEMA}
                """
            },
            {"role": "user", "content": "berapa jumlah dan total nominal transaksi qlola berdasarkan segmen pada bulan februari?"},
            {"role": "assistant", 
             "content": """ select segmentasi_cif, sum(freq_qlola), sum(sv_qlola)
                            from master_qlola
                            where ds='202602' """
            },
            {"role": "user", "content": "berikan top 20 cif yang tidak memiliki qlola dengan transaksi terbanyak untuk setiap kanwil dan segmen pada bulan januari!"},
            {"role": "assistant", 
             "content": """with cte as(
                        select ro, segmentasi_cif, a.cifno, sum(sv_trx) sv_trx
                        from master_qlola a
                        left join transaction_non_qlola b
                        on a.acctno=b.acctno
                        and a.ds=b.ds
                        where a.ds='202601'
                        and flag_qlola_cif=0
                        group by 1,2,3)
                        
                        SELECT ro, segmentasi_cif, cifno, sv_trx
                        FROM (
                            SELECT
                                t.*,
                                ROW_NUMBER() OVER (
                                    PARTITION BY ro, segmentasi_cif
                                    ORDER BY sv_trx DESC
                                ) AS rn
                            FROM cte t
                        ) x
                        WHERE rn <= 20 """
            },
            {"role": "user", "content": question}
        ]
    )
    return response.choices[0].message.content

def run_sql(sql):
    return pd.read_sql(sql, engine)

def generate_answer(question, df):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": """Kamu adalah seorang data analyst. Berikan penjelasan tentang hasil data secara jelas. Jangan hanya menjelaskan data, tapi juga
                 berikan insight yang bisa diambil dari data tersebut. Usahakan detail tapi tidak bertele-tele."""
            },
            {
                "role": "user",
                "content": f"""
Question: {question}

Result:
{df.to_string(index=False)}
"""
            }
        ]
    )
    return response.choices[0].message.content

def validate_sql(sql):
    forbidden = ["DROP", "DELETE", "UPDATE", "INSERT"]
    
    for word in forbidden:
        if word in sql.upper():
            raise Exception("Forbidden query")

    return True

def ask_db(question):
    try:
        sql = generate_sql(question)       # 1. LLM → SQL
        validate_sql(sql)                  # 2. Validasi SQL
        df = run_sql(sql)                  # 3. SQL → Data
        answer = generate_answer(question, df)  # 4. Data → LLM answer

        return {
            "sql": sql,
            "data": df,
            "answer": answer
        }
    except Exception as e:
        return {
            "error": str(e),
            "sql": None,
            "data": None,
            "answer": None
        }
