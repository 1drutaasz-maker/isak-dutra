# VIGIA / Quality Intelligence

**Machine learning aplicado a dados de processo da indústria de alimentos.**

Analisa lotes a partir de quatro indicadores numéricos: temperatura, pH, tempo de processo e rendimento. O motor treina um **Isolation Forest não supervisionado** usando lotes de referência e compara novos lotes. Retorna alertas e dimensões numericamente atípicas com desvio robusto (MAD).

O projeto é uma demonstração de engenharia e **não é uma ferramenta de certificação de segurança alimentar ou decisão sanitária**.

## Executar

```bash
cd vigia-quality
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Dashboard: http://localhost:8000  
Swagger: http://localhost:8000/docs  
Testes: `python -m pytest -q`  
Docker: `docker build -t vigia-quality . && docker run --rm -p 8000:8000 vigia-quality`

## API

`POST /api/analyze` recebe `reference` (mínimo de 50 lotes), `candidates` e `sensitivity` (0.02 a 0.25). Cada lote deve conter:

```json
{"batch_id":"L001","temperature_c":41.3,"ph":4.55,"duration_min":180,"yield_pct":92}
```

CSV no mesmo formato disponível para importar no painel.

## Decisões técnicas

- Referência separada dos lotes analisados (sem treinar sobre candidatos).
- Padronização de atributos e IsolationForest com semente fixa para reprodutibilidade.
- Scores de decisão preservados para comparação de prioridades.
- Mediana e desvio absoluto mediano para indicar atributos incomuns (não são explicações causais do modelo).
- Testes para detecção de exemplos extremos, validação e resultados determinísticos.

## Limites

O resultado depende da qualidade da referência, sensibilidade e contexto do processo. Variáveis e faixas são didáticas; não refletem critérios legais fixos. A taxa de contaminação é um parâmetro do algoritmo, não taxa real de defeitos. Faltam autenticação, banco, avaliação com rótulos reais, validação por especialista e observabilidade para produção.

Dados padrão são fictícios. Projeto produzido com assistência de IA para estudo e portfólio.
