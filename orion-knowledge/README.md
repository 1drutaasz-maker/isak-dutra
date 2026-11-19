# ORION / Knowledge Intelligence

Motor de conhecimento corporativo com **TF-IDF + similaridade cosseno**, chunking com sobreposição, rastreabilidade de fontes e integração opcional com **LLM**.

## Modo sem chave
Sem `OPENAI_API_KEY`, ORION não finge responder como um LLM: devolve trechos relevantes, identificadores e fontes (modo `retrieval_only`). Com a chave, envia o contexto selecionado para uma API de modelo e solicita uma resposta fundamentada. Requer internet e pode gerar custos.

## Executar

```bash
cd orion-knowledge
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Interface: http://localhost:8000  
API: http://localhost:8000/docs  
Testes: `pytest -q`  
Docker: `docker build -t orion-knowledge . && docker run --rm -p 8000:8000 -v orion-data:/app/var orion-knowledge`

Para geração opcional, configure `OPENAI_API_KEY` no ambiente do processo servidor (nunca no frontend). Modelo configurável por `OPENAI_MODEL`. Por padrão usa a API da OpenAI via HTTPS.

## API
- `POST /api/documents`: recebe `{"title":"...","content":"..."}`.
- `GET /api/documents`: lista metadados.
- `DELETE /api/documents/{id}`: apaga documento e trechos.
- `POST /api/ask`: `{"question":"...","top_k":4}` retorna resposta/modo/evidências.
- `GET /api/status`: modo e quantidade de documentos.

## Decisões técnicas
- Armazenamento SQLite com SQL parametrizado e integridade referencial.
- Chunking com sobreposição, referências de documentos e trechos.
- Ranking por TF-IDF e limiar de similaridade para não produzir respostas sem contexto.
- Chave da API mantida exclusivamente no servidor; LLM opcional.
- Prompt pede fundamentação e trata documentos recuperados como conteúdo não confiável.

## Limitações e segurança
Protótipo **não pronto para produção**: faltam autenticação, isolamento por empresa, controle de acesso, avaliação rigorosa de relevância, embeddings semânticos, defesa aprofundada contra prompt injection, limitação de requisições, observabilidade e ingestão de PDF. O índice de busca é reconstruído a cada pergunta e não é indicado para grande escala. Não envie informações confidenciais a provedores externos sem autorização e medidas de proteção. Respostas devem ser verificadas por humanos antes de decisões relevantes.

Projeto produzido com assistência de IA para estudo. Revise, teste e saiba explicar antes de apresentar em entrevistas.
