import os
import json
import re
import sqlite3
from fpdf import FPDF
from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn
from groq import Groq  # Importa o cliente da Groq API
from fastapi.templating import Jinja2Templates

app = FastAPI()

# 1. Inicializa o banco de dados SQLite e cria a tabela "aulas" se não existir
def init_db():
    conn = sqlite3.connect("aulas.db")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS aulas (
         id INTEGER PRIMARY KEY AUTOINCREMENT,
         titulo TEXT,
         professor TEXT,
         topicos TEXT,
         resumo TEXT,
         notas TEXT,
         data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

init_db()

templates = Jinja2Templates(directory="templates")

# -----------------------------------------------------------------------------
# 7. Rotas para as páginas
# -----------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/faq", response_class=HTMLResponse)
def faq(request: Request):
    return templates.TemplateResponse("faq.html", {"request": request})

@app.get("/preco", response_class=HTMLResponse)
def preco(request: Request):
    return templates.TemplateResponse("preco.html", {"request": request})

@app.get("/app", response_class=HTMLResponse)
def main_app(request: Request):
    return templates.TemplateResponse("app.html", {"request": request})

@app.get("/funcionalidades", response_class=HTMLResponse)
def funcionalidades(request: Request):
    return templates.TemplateResponse("funcionalidades.html", {"request": request})

# -----------------------------------------------------------------------------
# Endpoints de lógica do sistema
# -----------------------------------------------------------------------------
@app.post("/transcrever")
async def transcrever(file: UploadFile = File(...)):
    temp_filename = "temp_audio.wav"
    try:
        contents = await file.read()
        with open(temp_filename, "wb") as f:
            f.write(contents)

        # Transcrição usando o modelo whisper-large-v3-turbo via Groq API
        client = Groq(api_key="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")
        with open(temp_filename, "rb") as f:
            transcription_response = client.audio.transcriptions.create(
                file=(temp_filename, f.read()),
                model="whisper-large-v3-turbo",
                response_format="verbose_json",
            )
        transcricao = transcription_response.text.strip()

        # Prompt adaptado para o domínio de Educação
        prompt = f"""
Você é um assistente educacional. Analise a transcrição abaixo de uma aula ou palestra e extraia os seguintes dados para gerar anotações automatizadas:
- titulo: O título da aula/palestra
- professor: O nome do professor
- topicos: Os principais tópicos abordados
- resumo: Um resumo conciso da aula/palestra
- notas: Notas ou observações importantes

Retorne os dados no formato JSON exatamente como o exemplo abaixo:
{{
  "dados": {{
    "titulo": "Título da Aula",
    "professor": "Nome do Professor",
    "topicos": "Tópicos abordados",
    "resumo": "Resumo da Aula",
    "notas": "Notas importantes"
  }}
}}

Agora use esse formato para responder estritamente.

Transcrição:
"{transcricao}"
"""
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=1,
            max_completion_tokens=1024,
            top_p=1,
            stream=True,
            stop=None,
        )
        response_text = ""
        for chunk in completion:
            response_text += chunk.choices[0].delta.content or ""
        response_text = response_text.strip()

        try:
            result_json = json.loads(response_text)
            dados = result_json.get("dados", {})
        except json.JSONDecodeError:
            dados = {
                "titulo": "Aula_Sem_Titulo",
                "professor": "",
                "topicos": "",
                "resumo": "",
                "notas": ""
            }
        return JSONResponse(
            content={
                "transcricao": transcricao,
                "dados": dados
            },
            status_code=200
        )
    except Exception as e:
        return JSONResponse(content={"erro": str(e)}, status_code=500)
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

@app.post("/exportar")
async def exportar(dados: dict):
    try:
        titulo = dados.get("titulo", "Aula_Sem_Titulo")
        professor = dados.get("professor", "")
        topicos = dados.get("topicos", "")
        resumo = dados.get("resumo", "")
        notas = dados.get("notas", "")

        # Gera o PDF
        titulo_sanitizado = re.sub(r'[\\/*?:"<>|]', '', titulo)
        pdf_path = f"documentos/{titulo_sanitizado}.pdf"
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 10, "Resumo da Aula", ln=1, align="C")
        pdf.ln(5)
        pdf.cell(0, 10, "Título: " + titulo, ln=1)
        pdf.cell(0, 10, "Professor: " + professor, ln=1)
        pdf.cell(0, 10, "Tópicos: " + topicos, ln=1)
        pdf.cell(0, 10, "Resumo: " + resumo, ln=1)
        pdf.cell(0, 10, "Notas: " + notas, ln=1)
        pdf.output(pdf_path)

        # Salva os dados no banco de dados "aulas"
        conn = sqlite3.connect("aulas.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO aulas (titulo, professor, topicos, resumo, notas) VALUES (?, ?, ?, ?, ?)",
            (titulo, professor, topicos, resumo, notas)
        )
        conn.commit()
        conn.close()

        return JSONResponse(
            content={
                "pdf_gerado": pdf_path,
                "mensagem": "PDF exportado e dados salvos com sucesso."
            },
            status_code=200
        )
    except Exception as e:
        return JSONResponse(content={"erro": str(e)}, status_code=500)

@app.get("/consultar")
def consultar(titulo: str):
    try:
        conn = sqlite3.connect("aulas.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM aulas WHERE titulo = ?", (titulo,))
        rows = cursor.fetchall()
        conn.close()
        if rows:
            aulas = [dict(row) for row in rows]
            return JSONResponse(content={"aulas": aulas}, status_code=200)
        else:
            return JSONResponse(
                content={"mensagem": "Nenhuma aula encontrada com esse título."},
                status_code=404
            )
    except Exception as e:
        return JSONResponse(content={"erro": str(e)}, status_code=500)

@app.post("/diagnosticar")
def diagnosticar(dados: dict):
    # Neste contexto, este endpoint pode ser usado para gerar um resumo final ou destaques adicionais.
    try:
        topicos = dados.get("topicos", "")
        resumo = dados.get("resumo", "")
        prompt = f"""
Você é um assistente educacional. Com base nos tópicos e resumo abaixo, forneça um resumo final destacando os pontos mais importantes da aula.
Tópicos: {topicos}
Resumo: {resumo}

Responda apenas com o resumo final.
"""
        
        client = Groq(api_key="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")
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=1,
            max_completion_tokens=1024,
            top_p=1,
            stream=True,
            stop=None,
        )
        resumo_final = ""
        for chunk in completion:
            resumo_final += chunk.choices[0].delta.content or ""
        resumo_final = resumo_final.strip()
        return JSONResponse(content={"resumo_final": resumo_final}, status_code=200)
    except Exception as e:
        return JSONResponse(content={"erro": str(e)}, status_code=500)

# -----------------------------------------------------------------------------
# Inicia o servidor
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
