import os
import uuid
import json
import gc
from faster_whisper import WhisperModel
from groq import Groq
from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv, dotenv_values 
# carregando variáveis do arquivo.env
load_dotenv() 

# acessando e imprimindo valor
groq_api = os.getenv("GROQ_API_KEY")


app = FastAPI()

# Configuração de arquivos estáticos e templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Configuração CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("Carregando o modelo faster-whisper 'base'...")
whisper_model = WhisperModel("base")
print("Modelo faster-whisper carregado com sucesso!")

@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    return templates.TemplateResponse("landing_page.html", {"request": request})

@app.get("/app", response_class=HTMLResponse, name="app_home")
async def app_home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/meus_conteudos", response_class=HTMLResponse, name="meus_conteudos")
async def meus_conteudos(request: Request):
    return templates.TemplateResponse("meus_conteudos.html", {"request": request})

@app.post("/transcrever")
async def transcrever(file: UploadFile = File(...)):
    temp_filename = f"temp_audio_{uuid.uuid4()}.wav"
    
    try:
        # Salvar arquivo temporário
        with open(temp_filename, "wb") as f:
            f.write(await file.read())

        # Transcrição
        segments, _ = whisper_model.transcribe(temp_filename, language="pt")
        texto_transcrito = " ".join(segment.text.strip() for segment in segments)
        
        # Dividir a transcrição se for muito longa
        max_length = 3000  # Número seguro de caracteres
        texto_para_analise = texto_transcrito[:max_length] if len(texto_transcrito) > max_length else texto_transcrito

        # Prompt otimizado
        prompt = f"""
        Você é um assistente educacional que ajuda alunos a anotar suas aulas.

        Analise a transcrição abaixo e gere **somente um JSON válido**, com os seguintes campos:
        - "titulo": um título breve (até 7 palavras), que represente o tema da aula.
        - "resumo": Resuma a aula como se estivesse fazendo anotações detalhadas, explicando os conceitos com exemplos, técnicas explicadas pelo professor e organizando as informações em parágrafos separados para facilitar a leitura. Deve conter **frases completas**, com a explicação dos principais conceitos, exemplos mencionados na aula e organização por tópicos e subtópicos se necessário.
        - "materiais": uma lista simples de strings, cada uma contendo um recurso complementar no formato: [Título do Recurso](URL).

        Instruções importantes:
        - O campo "resumo" deve conter **conteúdo detalhado** e não apenas um resumo genérico.
        - Imagine que outro aluno irá estudar apenas com essas anotações: elas devem ser claras, completas e organizadas.
        - O campo "materiais" deve ser uma **lista simples de strings**. **Não use listas dentro da lista.**

        Exemplo de saída:
        {{
        "titulo": "Aula de Inglês - Verbos no Tempo",
        "resumo": "Nesta aula foram abordados os tempos verbais do verbo 'to study'.\n\nTópicos:\n\n1. Presente Simples:\n- Forma: I study / You study / He studies.\n- Exemplos: I study every day. He studies at night.\n\n2. Passado Simples:\n- Forma: I studied / You studied.\n- Regras para verbos terminados em -y: study → studied.\n\n3. Futuro Simples:\n- Forma: I will study / I'll study.\n- Exemplos: I will study tomorrow morning.\n\nForam discutidas diferenças de uso e situações cotidianas relacionadas aos tempos verbais...",
        "materiais": [
            "[Vídeo: Tenses Explained (YouTube)](https://youtube.com/exemplo1)",
            "[Artigo: Guia do Passado Simples](https://exemplo.com/past)",
            "[Exercícios: Tempos Verbais](https://exemplo.com/exercicios)"
        ]
        }}

        TRANSCRIÇÃO:
        {texto_para_analise}
        """




        # Chamada à API Groq
        try:
            client = Groq(api_key= groq_api)
            completion = client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            
            resposta = completion.choices[0].message.content
            
            # Processar a resposta JSON
            try:
                if isinstance(resposta, str):
                    dados = json.loads(resposta)
                else:
                    dados = resposta

                # Extrair informações do JSON
                titulo = dados.get("titulo", "Aula - " + file.filename.split(".")[0][:20])
                resumo = dados.get("resumo", "Não foi possível gerar o resumo")
                materiais = dados.get("materiais", [])

                # Formatar materiais corretamente
                materiais_formatados = []
                for material in materiais:
                    if isinstance(material, str):
                        materiais_formatados.append(material)
                    elif isinstance(material, list):
                        materiais_formatados.extend(material)

                # Criar saída formatada
                resumo_formatado = f"""
                <div class="result-section">
                    <h3>{titulo}</h3>
                    <div class="resumo-content">
                        {resumo}
                    </div>
                """

                if materiais_formatados:
                    resumo_formatado += """
                    <div class="materiais-section">
                        <h4>Materiais Complementares:</h4>
                        <ul>"""
                    for material in materiais_formatados:
                        resumo_formatado += f"<li>{material}</li>"
                    resumo_formatado += "</ul></div>"

                resumo_formatado += "</div>"

                return JSONResponse({
                    "transcricao": texto_transcrito,
                    "titulo": titulo,
                    "resumo": resumo_formatado
                })

            except json.JSONDecodeError as json_error:
                print(f"Erro ao decodificar JSON: {str(json_error)}")
                # Se não for JSON válido, usar o texto direto
                return JSONResponse({
                    "transcricao": texto_transcrito,
                    "titulo": "Aula - " + file.filename.split(".")[0][:20],
                    "resumo": f"<div class='resumo-content'>{resposta}</div>"
                })
                
        except Exception as api_error:
            print(f"Erro na API Groq: {str(api_error)}")
            # Fallback básico se a API falhar
            return JSONResponse({
                "transcricao": texto_transcrito,
                "titulo": "Aula - " + file.filename.split(".")[0][:20],
                "resumo": "<div class='resumo-content'>Resumo não disponível devido a limitações técnicas</div>"
            })

    except Exception as e:
        print(f"Erro geral: {str(e)}")
        return JSONResponse(
            content={
                "erro": str(e),
                "solucao": "Tente arquivos menores ou aguarde para tentar novamente"
            },
            status_code=500
        )

    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

if __name__ == "__main__":

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
