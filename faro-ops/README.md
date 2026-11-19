# FARO / Operations Intelligence

Sistema de inteligência operacional para previsão de vendas e decisões de reposição.

**Stack:** Python · FastAPI · Pydantic · scikit-learn · REST · testes com pytest · Docker · HTML/CSS/JS.

### Executar
\`\`\`bash
cd faro-ops
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
\`\`\`

Dashboard: http://localhost:8000 · API interativa: http://localhost:8000/docs

Docker: \`docker build -t faro-ops . && docker run --rm -p 8000:8000 faro-ops\`

Testes: \`pytest -q\`

### Contrato API
\`POST /api/forecast\` recebe o SKU, estoque, prazo de reposição, horizonte e histórico cronológico diário no formato \`[{ "date": "2026-01-01", "units": 35 }]\` (mínimo de 28 dias, sem lacunas). Retorna valores previstos, desempenho temporal e recomendação de reposição.

### Decisões técnicas
- 11 atributos derivados de valores passados (lags, médias, volatilidade e dia da semana).
- Holdout cronológico de 20% para reduzir vazamento temporal; comparação com baseline "último dia".
- Re-treino no histórico integral e previsão recursiva, sem olhar vendas futuras.
- Faixas de previsão **heurísticas**, não intervalos de confiança calibrados.
- Recomendação baseada na demanda estimada durante o lead time + estoque de segurança.
- CSV importado no navegador, com dados sintéticos disponíveis para demonstração.

### Limites
Protótipo para portfólio, **não implantado em produção**, sem autenticação, banco, integração ERP ou MLOps. Resultados dependem da qualidade e quantidade dos dados. Sem garantia de ganho sobre baseline ou de acurácia futura.

Código produzido com assistência de IA para estudo e revisão; leia, teste e saiba explicar antes de usar em entrevista.
