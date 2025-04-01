import os
import json
import re
import sqlite3
from fpdf import FPDF
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn
from groq import Groq  # Importa o cliente da Groq API

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

# -----------------------------------------------------------------------------
# 2. Página de Landing ("/") adaptada para Educação
# -----------------------------------------------------------------------------
HOME_HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>EduVox - Landing Page</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link href="https://fonts.googleapis.com/css?family=Roboto:400,500&display=swap" rel="stylesheet">
  <style>
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: 'Roboto', sans-serif;
      background-color: #f4f7f6;
    }
    nav {
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: #fff;
      padding: 15px 40px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .logo {
      font-size: 20px;
      font-weight: bold;
      color: #3498db;
    }
    .menu a {
      margin-left: 20px;
      text-decoration: none;
      color: #333;
      font-weight: 500;
      transition: color 0.3s;
    }
    .menu a:hover {
      color: #3498db;
    }
    .hero {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
      padding: 100px 20px;
    }
    .hero h1 {
      font-size: 36px;
      margin-bottom: 20px;
      color: #333;
    }
    .hero p {
      font-size: 18px;
      color: #666;
      max-width: 600px;
      margin-bottom: 40px;
    }
    .hero button {
      background: #3498db;
      color: #fff;
      border: none;
      padding: 15px 30px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 16px;
      transition: background 0.3s;
    }
    .hero button:hover {
      background: #2980b9;
    }
    footer {
      text-align: center;
      padding: 20px;
      color: #999;
    }
    @media (max-width: 768px) {
      nav {
        flex-direction: column;
        align-items: flex-start;
      }
      .menu {
        margin-top: 10px;
      }
      .menu a {
        margin-left: 0;
        margin-right: 10px;
      }
      .hero h1 {
        font-size: 28px;
      }
      .hero p {
        font-size: 16px;
      }
    }
  </style>
</head>
<body>
  <nav>
    <div class="logo">EduVox</div>
    <div class="menu">
      <a href="/funcionalidades">Funcionalidades</a>
      <a href="/faq">FAQ</a>
      <a href="/preco">Preço</a>
      <a href="/app">Acessar</a>
      <a href="#cadastro">Cadastre-se já</a>
    </div>
  </nav>

  <section class="hero">
    <h1>Revolucione seus estudos com transcrições e resumos automatizados</h1>
    <p>Revise aulas e palestras com anotações precisas e resumos inteligentes para facilitar seu aprendizado.</p>
    <button onclick="location.href='/app'">Acessar</button>
  </section>

  <footer>
    &copy; 2025 EduVox. Todos os direitos reservados.
  </footer>
</body>
</html>
"""

# -----------------------------------------------------------------------------
# 3. Página FAQ ("/faq") para o domínio Educação
# -----------------------------------------------------------------------------
FAQ_HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>EduVox - FAQ</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link href="https://fonts.googleapis.com/css?family=Roboto:400,500&display=swap" rel="stylesheet">
  <style>
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: 'Roboto', sans-serif;
      background-color: #f4f7f6;
      padding: 20px;
    }
    h1 {
      text-align: center;
      margin-bottom: 40px;
      color: #333;
    }
    .faq-item {
      background: #fff;
      margin-bottom: 20px;
      padding: 20px;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .faq-item h2 {
      margin: 0 0 10px 0;
      font-size: 18px;
      color: #3498db;
    }
    .faq-item p {
      margin: 0;
      color: #555;
    }
    .back-link {
      display: inline-block;
      margin-top: 20px;
      text-decoration: none;
      color: #3498db;
      font-weight: 500;
    }
    @media (max-width: 600px) {
      body { padding: 10px; }
    }
  </style>
</head>
<body>
  <h1>FAQ - Perguntas Frequentes</h1>

  <div class="faq-item">
    <h2>1. O que é o EduVox?</h2>
    <p>EduVox é uma plataforma que auxilia estudantes a obter transcrições de aulas e gerar resumos e anotações automáticas.</p>
  </div>

  <div class="faq-item">
    <h2>2. Como o EduVox funciona?</h2>
    <p>Basta enviar o áudio ou vídeo da aula/palestra e o EduVox processa o conteúdo, extraindo os tópicos principais e gerando um resumo.</p>
  </div>

  <div class="faq-item">
    <h2>3. Preciso instalar algum software?</h2>
    <p>Não. Tudo funciona diretamente pelo navegador.</p>
  </div>

  <a class="back-link" href="/">Voltar à Página Inicial</a>
</body>
</html>
"""

# -----------------------------------------------------------------------------
# 4. Página Preço ("/preco") para o domínio Educação
# -----------------------------------------------------------------------------
PRECO_HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>EduVox - Preço</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link href="https://fonts.googleapis.com/css?family=Roboto:400,500&display=swap" rel="stylesheet">
  <style>
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: 'Roboto', sans-serif;
      background-color: #f4f7f6;
      padding: 20px;
    }
    h1 {
      text-align: center;
      margin-bottom: 40px;
      color: #333;
    }
    .pricing-plan {
      background: #fff;
      margin: 20px auto;
      max-width: 600px;
      padding: 20px;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .pricing-plan h2 {
      margin: 0 0 10px 0;
      font-size: 20px;
      color: #3498db;
    }
    .pricing-plan p {
      margin: 5px 0;
      color: #555;
    }
    .price {
      font-size: 24px;
      color: #333;
      margin-top: 10px;
      margin-bottom: 20px;
    }
    .back-link {
      display: inline-block;
      margin-top: 20px;
      text-decoration: none;
      color: #3498db;
      font-weight: 500;
    }
    @media (max-width: 600px) {
      body { padding: 10px; }
      .pricing-plan { margin: 10px auto; width: 100%; }
    }
  </style>
</head>
<body>
  <h1>Planos e Preços</h1>

  <div class="pricing-plan">
    <h2>Plano Básico</h2>
    <p>Ideal para estudantes individuais.</p>
    <div class="price">R$ 29,90 / mês</div>
    <p>- Transcrição de até 50 aulas por mês</p>
    <p>- Geração de resumos e tópicos</p>
    <p>- Suporte via e-mail</p>
  </div>

  <div class="pricing-plan">
    <h2>Plano Premium</h2>
    <p>Perfeito para escolas e cursos online.</p>
    <div class="price">R$ 59,90 / mês</div>
    <p>- Transcrição de até 150 aulas por mês</p>
    <p>- Geração de resumos, tópicos e anotações detalhadas</p>
    <p>- Integração com plataformas educacionais</p>
    <p>- Suporte prioritário</p>
  </div>

  <a class="back-link" href="/">Voltar à Página Inicial</a>
</body>
</html>
"""

# -----------------------------------------------------------------------------
# 5. Página com as Funcionalidades ("/app") adaptada para Educação
# -----------------------------------------------------------------------------
APP_HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>EduVox - Transcrição e Resumos</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link href="https://fonts.googleapis.com/css?family=Roboto:400,500&display=swap" rel="stylesheet">
  <style>
    * { box-sizing: border-box; }
    body { 
      font-family: 'Roboto', sans-serif; 
      margin: 0; 
      padding: 0; 
      background: #f4f7f6; 
      display: flex; 
      justify-content: center; 
      align-items: center; 
      min-height: 100vh; 
    }
    .container { 
      background: #fff; 
      padding: 30px; 
      border-radius: 8px; 
      box-shadow: 0 2px 8px rgba(0,0,0,0.1); 
      width: 90%; 
      max-width: 600px; 
      margin: 20px;
    }
    h1 { 
      text-align: center; 
      margin-bottom: 20px; 
      color: #333;
      font-size: 24px;
    }
    .section {
      margin-bottom: 20px;
    }
    .section label {
      display: block;
      margin-bottom: 5px;
      font-weight: 500;
      color: #555;
    }
    .section input[type="text"],
    .section textarea {
      width: 100%;
      padding: 10px;
      border: 1px solid #ddd;
      border-radius: 4px;
      margin-bottom: 10px;
      font-size: 14px;
    }
    button {
      background: #3498db;
      color: #fff;
      border: none;
      padding: 10px 20px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 14px;
      transition: background 0.3s;
      margin-right: 10px;
    }
    button:disabled {
      background: #95a5a6;
      cursor: not-allowed;
    }
    button:hover:not(:disabled) {
      background: #2980b9;
    }
    .btn-group {
      text-align: center;
      margin-bottom: 20px;
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      justify-content: center;
    }
    #status {
      text-align: center;
      font-weight: 500;
      color: #555;
      margin-bottom: 20px;
    }
    #progressBar {
      width: 100%;
      background: #ddd;
      border-radius: 4px;
      overflow: hidden;
      margin-bottom: 20px;
      display: none;
    }
    #progressBar div {
      height: 10px;
      width: 0;
      background: #3498db;
      transition: width 0.3s;
    }
    #transcricaoText {
      white-space: pre-wrap; 
      background: #f9f9f9; 
      padding: 10px; 
      border-radius: 4px;
    }
    .back-link-fixo {
      position: fixed;   
      bottom: 10px;      
      left: 10px;        
      text-decoration: none;
      color: #3498db;
      font-weight: 500;
      background-color: #fff;
      padding: 5px 10px;
      border-radius: 4px;
      box-shadow: 0 1px 4px rgba(0,0,0,0.2);
    }
    .back-link-fixo:hover {
      text-decoration: underline;
    }
    @media (max-width: 600px) {
      .btn-group {
        flex-direction: column;
        gap: 10px;
      }
      button { width: 100%; }
      h1 { font-size: 20px; }
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>EduVox - Transcrição e Resumos de Aulas</h1>
    <p style="text-align: center;">Envie o áudio ou vídeo da aula/palestra para gerar transcrições, resumos e extração de tópicos.</p>
    
    <div class="btn-group">
      <button id="btnStart">Iniciar Gravação</button>
      <button id="btnStop" disabled>Parar Gravação</button>
    </div>
    
    <div class="section">
      <h2 style="font-size: 16px; margin-bottom: 10px;">Enviar Áudio/Vídeo</h2>
      <input type="file" id="audioFile" accept="audio/*, video/*">
      <button id="btnUpload">Enviar Arquivo</button>
    </div>

    <div id="progressBar"><div></div></div>
    <div id="status"></div>

    <!-- Seção de transcrição -->
    <div id="transcricao" class="section" style="display:none;">
      <h2 style="font-size: 16px; margin-bottom: 10px;">Transcrição</h2>
      <p id="transcricaoText"></p>
    </div>

    <!-- Seção de edição dos dados -->
    <div id="edicao" class="section" style="display:none;">
      <h2 style="font-size: 16px; margin-bottom: 10px;">Revisão e Anotações</h2>
      <form id="editForm">
        <label>Título da Aula:</label>
        <input type="text" id="titulo_aula" />

        <label>Nome do Professor:</label>
        <input type="text" id="nome_professor" />

        <label>Tópicos Abordados:</label>
        <textarea id="topicos" rows="2"></textarea>

        <label>Resumo da Aula:</label>
        <textarea id="resumo" rows="2"></textarea>

        <label>Notas Importantes:</label>
        <textarea id="notas" rows="2"></textarea>

        <div style="text-align: center; margin-top: 10px;">
          <button type="button" id="btnExportar">Exportar e Salvar PDF</button>
        </div>
      </form>
    </div>

    <!-- Seção para consulta no banco de dados -->
    <div id="consulta" class="section">
      <h2 style="font-size: 16px; margin-bottom: 10px;">Consultar Aulas</h2>
      <input type="text" id="consulta_titulo" placeholder="Digite o título da aula">
      <button type="button" id="btnConsultar">Consultar</button>
      <div id="resultadoConsulta" style="margin-top: 10px;"></div>
    </div>
  </div>
  <!-- Link fixo no canto inferior esquerdo -->
  <a href="/" class="back-link-fixo">Voltar à Página Inicial</a>
  <script>
    let mediaRecorder;
    let audioChunks = [];
    const btnStart = document.getElementById("btnStart");
    const btnStop = document.getElementById("btnStop");
    const btnUpload = document.getElementById("btnUpload");
    const audioFileInput = document.getElementById("audioFile");
    const statusEl = document.getElementById("status");
    const progressBar = document.getElementById("progressBar");
    const progressDiv = progressBar.querySelector("div");
    const transcricaoEl = document.getElementById("transcricao");
    const transcricaoTextEl = document.getElementById("transcricaoText");

    // Inicia gravação de áudio
    btnStart.addEventListener("click", async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        mediaRecorder.addEventListener("dataavailable", event => {
          audioChunks.push(event.data);
        });
        mediaRecorder.addEventListener("stop", async () => {
          const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
          const formData = new FormData();
          formData.append("file", audioBlob, "gravacao.wav");
          await enviarAudio(formData);
        });
        mediaRecorder.start();
        btnStart.disabled = true;
        btnStop.disabled = false;
        statusEl.textContent = "Gravando...";
        progressBar.style.display = "block";
        progressDiv.style.width = "0%";
      } catch (err) {
        console.error(err);
        statusEl.textContent = "Erro ao acessar o microfone.";
      }
    });

    // Para gravação de áudio
    btnStop.addEventListener("click", () => {
      mediaRecorder.stop();
      btnStart.disabled = false;
      btnStop.disabled = true;
      statusEl.textContent = "Gravação parada. Processando...";
    });

    // Envio de arquivo de áudio/vídeo
    btnUpload.addEventListener("click", async () => {
      const files = audioFileInput.files;
      if (!files || files.length === 0) {
        statusEl.textContent = "Selecione um arquivo primeiro.";
        return;
      }
      const formData = new FormData();
      formData.append("file", files[0], files[0].name);
      statusEl.textContent = "Enviando arquivo para o servidor...";
      await enviarAudio(formData);
    });

    async function enviarAudio(formData) {
      try {
        const response = await fetch("/transcrever", {
          method: "POST",
          body: formData
        });
        const data = await response.json();
        statusEl.textContent = "Processamento concluído!";
        transcricaoEl.style.display = "block";
        transcricaoTextEl.textContent = data.transcricao.trim();

        // Preenche os campos com os dados extraídos
        if (data.dados) {
          document.getElementById("titulo_aula").value = data.dados.titulo || "";
          document.getElementById("nome_professor").value = data.dados.professor || "";
          document.getElementById("topicos").value = data.dados.topicos || "";
          document.getElementById("resumo").value = data.dados.resumo || "";
          document.getElementById("notas").value = data.dados.notas || "";
        }
      } catch (error) {
        console.error(error);
        statusEl.textContent = "Erro ao enviar arquivo para o servidor.";
      } finally {
        progressBar.style.display = "none";
      }
    }

    // Exporta dados e salva PDF
    document.getElementById("btnExportar").addEventListener("click", async () => {
      statusEl.textContent = "Exportando e salvando PDF...";
      const dados = {
        titulo: document.getElementById("titulo_aula").value,
        professor: document.getElementById("nome_professor").value,
        topicos: document.getElementById("topicos").value,
        resumo: document.getElementById("resumo").value,
        notas: document.getElementById("notas").value
      };
      try {
        const exportResponse = await fetch("/exportar", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(dados)
        });
        const exportData = await exportResponse.json();
        if (exportResponse.ok) {
          statusEl.textContent = exportData.mensagem || "PDF gerado com sucesso!";
          alert("PDF gerado em: " + exportData.pdf_gerado);
        } else {
          statusEl.textContent = "Erro na exportação: " + exportData.erro;
        }
      } catch (error) {
        console.error(error);
        statusEl.textContent = "Erro ao exportar PDF.";
      }
    });

    // Consulta aulas no banco de dados
    document.getElementById("btnConsultar").addEventListener("click", async () => {
      const titulo = document.getElementById("consulta_titulo").value;
      if (!titulo) {
        statusEl.textContent = "Por favor, insira o título da aula para consulta.";
        return;
      }
      try {
        const response = await fetch(`/consultar?titulo=${encodeURIComponent(titulo)}`);
        const result = await response.json();
        const resultadoDiv = document.getElementById("resultadoConsulta");
        resultadoDiv.innerHTML = "";
        if (response.ok) {
          if (result.aulas && result.aulas.length > 0) {
            let html = `<h3 style="margin-bottom: 10px;">Resultados da consulta:</h3>`;
            result.aulas.forEach(aula => {
              html += `
                <div style="background: #fff; border: 1px solid #ddd; border-radius: 4px; padding: 15px; margin-bottom: 10px; box-shadow: 0 1px 4px rgba(0,0,0,0.1);">
                  <p><strong>ID:</strong> ${aula.id}</p>
                  <p><strong>Título:</strong> ${aula.titulo}</p>
                  <p><strong>Professor:</strong> ${aula.professor}</p>
                  <p><strong>Tópicos:</strong> ${aula.topicos}</p>
                  <p><strong>Resumo:</strong> ${aula.resumo}</p>
                  <p><strong>Notas:</strong> ${aula.notas}</p>
                  <p><strong>Data de Criação:</strong> ${aula.data_criacao}</p>
                </div>
              `;
            });
            resultadoDiv.innerHTML = html;
          } else {
            resultadoDiv.innerHTML = `<div style="background: #fff; border: 1px solid #ddd; border-radius: 4px; padding: 15px;">Nenhuma aula encontrada.</div>`;
          }
        } else {
          resultadoDiv.innerHTML = `<div style="background: #fff; border: 1px solid #ddd; border-radius: 4px; padding: 15px;">${result.mensagem || "Nenhuma aula encontrada."}</div>`;
        }
      } catch (error) {
        console.error(error);
        statusEl.textContent = "Erro ao consultar aula.";
      }
    });
  </script>
</body>
</html>
"""

# -----------------------------------------------------------------------------
# 6. Nova página: Funcionalidades ("/funcionalidades") para Educação
# -----------------------------------------------------------------------------
FUNCIONALIDADES_HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>EduVox - Funcionalidades</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link href="https://fonts.googleapis.com/css?family=Roboto:400,500&display=swap" rel="stylesheet">
  <style>
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: 'Roboto', sans-serif;
      background-color: #f4f7f6;
      padding: 20px;
    }
    .container {
      max-width: 800px;
      margin: 0 auto;
      background: #fff;
      padding: 30px;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    h1 {
      text-align: center;
      color: #333;
      margin-bottom: 20px;
      font-size: 28px;
    }
    .highlight {
      background: #e8f4fd;
      border-left: 4px solid #3498db;
      padding: 15px;
      font-size: 18px;
      color: #333;
      margin-bottom: 30px;
      text-align: center;
    }
    .func-list {
      list-style-type: none;
      padding: 0;
      font-size: 16px;
      color: #555;
    }
    .func-list li {
      padding: 10px;
      border-bottom: 1px solid #eee;
    }
    .func-list li:last-child {
      border-bottom: none;
    }
    .back-link {
      display: inline-block;
      margin-top: 20px;
      text-decoration: none;
      color: #3498db;
      font-weight: 500;
    }
    @media (max-width: 600px) {
      .container { padding: 20px; }
      h1 { font-size: 24px; }
      .highlight { font-size: 16px; }
      .func-list li { font-size: 14px; }
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>Funcionalidades</h1>
    <div class="highlight">
      Conheça as funcionalidades que farão a diferença no seu dia a dia.
    </div>
    <ul class="func-list">
      <li>Transcrição de aulas ou palestras, permitindo que estudantes revisem o conteúdo e tenham anotações automatizadas;</li>
      <li>Geração de resumos e extração de tópicos importantes a partir de vídeos e áudios de cursos.</li>
    </ul>
    <a class="back-link" href="/">Voltar à Página Inicial</a>
  </div>
</body>
</html>
"""

# -----------------------------------------------------------------------------
# 7. Rotas para as páginas
# -----------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def home():
    return HOME_HTML

@app.get("/faq", response_class=HTMLResponse)
def faq():
    return FAQ_HTML

@app.get("/preco", response_class=HTMLResponse)
def preco():
    return PRECO_HTML

@app.get("/app", response_class=HTMLResponse)
def main_app():
    return APP_HTML

@app.get("/funcionalidades", response_class=HTMLResponse)
def funcionalidades():
    return FUNCIONALIDADES_HTML

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
