import basedosdados as bd
import pandas as pd

billing_id = 'ID_DO_PROJETO_BILLADO'

query_agg = """
SELECT
    ano,
    admitidos_desligados,
    CASE
        WHEN salario_mensal < 1000 THEN '< 1 mil'
        WHEN salario_mensal >= 1000 AND salario_mensal < 2000 THEN '1–2 mil'
        WHEN salario_mensal >= 2000 AND salario_mensal < 3000 THEN '2–3 mil'
        WHEN salario_mensal >= 3000 THEN '> 3 mil'
        ELSE 'Desconhecido'
    END as faixa_salario,
    COUNT(*) as quantidade
FROM `basedosdados.br_me_caged.microdados_antigos`
WHERE ano IN (2017, 2018, 2019)
  AND sigla_uf = 'RS'
  AND salario_mensal IS NOT NULL
GROUP BY ano, admitidos_desligados, faixa_salario
"""

print("Executando consulta agregada (2017-2019)...")

df_agg = bd.read_sql(
    query=query_agg,
    billing_project_id=billing_id
)

arquivo_agg = "caged_rs_2017_2019_agregado.parquet"

print(f"Salvando em {arquivo_agg}...")

df_agg.to_parquet(
    arquivo_agg,
    index=False,
    compression="snappy"
)

print("Nova extração concluída!")
