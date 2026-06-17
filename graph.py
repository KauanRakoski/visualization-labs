import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.io as pio

pio.templates.default = "plotly_white"

DATA_PATH = "caged_rs_2019.parquet"
DATA_PATH_AGG = "caged_rs_2017_2019_agregado.parquet"

SALARY_COLUMNS = [
    "mes",
    "salario_mensal",
    "sexo",
    "admitidos_desligados",
    "quantidade_horas_contratadas",
]

SALARY_RANGES = ["< 1 mil", "1–2 mil", "2–3 mil", "> 3 mil"]

st.set_page_config(layout="wide", page_title="CAGED RS 2019", page_icon="📊")
st.title("📊 CAGED RS 2019 - Mercado de Trabalho")
st.markdown("Análise de admissões, desligamentos e salários no Rio Grande do Sul.")

@st.cache_data
def load_caged_dataset() -> pd.DataFrame:
    return pd.read_parquet(DATA_PATH, columns=SALARY_COLUMNS)

@st.cache_data
def load_aggregated_dataset() -> pd.DataFrame:
    return pd.read_parquet(DATA_PATH_AGG)

def compute_monthly_average(data: pd.DataFrame) -> pd.DataFrame:
    return (
        data.groupby("mes", as_index=False)
        .agg(salario_medio=("salario_mensal", "mean"))
        .sort_values("mes")
    )

def compute_gender_average(data: pd.DataFrame) -> pd.DataFrame:
    gender_map = {
        "01": "Masculino",
        "02": "Feminino",
    }
    temp = data.copy()
    temp["sexo"] = temp["sexo"].map(gender_map).fillna(temp["sexo"])
    return (
        temp.groupby("sexo", as_index=False)
        .agg(salario_medio=("salario_mensal", "mean"))
    )

def salary_range(value: float) -> str:
    if value < 1000:
        return "< 1 mil"
    if value < 2000:
        return "1–2 mil"
    if value < 3000:
        return "2–3 mil"
    return "> 3 mil"

def prepare_pyramid_data(data: pd.DataFrame) -> pd.DataFrame:
    temp = data.copy()
    temp["faixa_salario"] = temp["salario_mensal"].apply(salary_range)

    admissions = (
        temp[temp["admitidos_desligados"] == "01"]
        .groupby("faixa_salario")
        .size()
        .reset_index(name="valor")
    )
    admissions["tipo"] = "Admissões"
    admissions["valor_absoluto"] = admissions["valor"]

    dismissals = (
        temp[temp["admitidos_desligados"] == "02"]
        .groupby("faixa_salario")
        .size()
        .reset_index(name="valor")
    )
    dismissals["tipo"] = "Desligamentos"
    dismissals["valor"] = -dismissals["valor"]
    dismissals["valor_absoluto"] = dismissals["valor"].abs()

    pyramid = pd.concat([admissions, dismissals], ignore_index=True)

    pyramid["faixa_salario"] = pd.Categorical(
        pyramid["faixa_salario"],
        categories=SALARY_RANGES,
        ordered=True,
    )

    return pyramid.sort_values("faixa_salario")

def build_metrics(average_salary: float) -> None:
    cesta_basica_poa = 506.30
    preco_kwid = 33190

    st.subheader("💰 Visão geral")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("📊 Salário médio anual", f"R$ {average_salary:,.2f}".replace(",", "."))

    with col2:
        st.metric(
            "🛒 Cesta básica (% do salário)",
            f"{(cesta_basica_poa / average_salary) * 100:.2f}%".replace(".", ",")
        )

    with col3:
        st.metric(
            "🚗 Meses para comprar um Kwid",
            f"{(preco_kwid / average_salary):.1f} meses".replace(".", ",")
        )

def build_comparison_charts(
    monthly_data: pd.DataFrame,
    gender_data: pd.DataFrame
) -> None:
    st.subheader("📊 Análises comparativas")

    col1, col2 = st.columns(2)

    fig_line = px.line(
        monthly_data,
        x="mes",
        y="salario_medio",
        markers=True,
        title="Salário médio por mês",
        color_discrete_sequence=["#1f77b4"]
    )
    fig_line.update_layout(xaxis=dict(tickmode="linear", dtick=1))

    fig_gender = px.bar(
        gender_data,
        x="sexo",
        y="salario_medio",
        text_auto=".2f",
        title="Salário médio anual por sexo",
        color="sexo",
        color_discrete_map={"Masculino": "#1f77b4", "Feminino": "#e377c2"}
    )
    fig_gender.update_layout(showlegend=False)

    with col1:
        st.plotly_chart(fig_line, use_container_width=True)

    with col2:
        st.plotly_chart(fig_gender, use_container_width=True)

def build_pyramid_chart(pyramid_data: pd.DataFrame) -> None:
    st.subheader("📈 Saldo de Empregos por Faixa Salarial")

    balance_data = (
        pyramid_data
        .groupby("faixa_salario", observed=True)["valor"]
        .sum()
        .reset_index()
    )

    fig_pyramid = px.bar(
        balance_data,
        x="valor",
        y="faixa_salario",
        orientation="h",
        title="Saldo (Admissões - Desligamentos)",
        category_orders={
            "faixa_salario": SALARY_RANGES[::-1]
        },
        color="valor",
        color_continuous_scale=px.colors.diverging.RdYlGn,
        color_continuous_midpoint=0
    )
    fig_pyramid.add_vline(x=0, line_dash="dash", line_color="#333333")

    st.plotly_chart(fig_pyramid, use_container_width=True)

def build_salary_vs_hours_chart(data: pd.DataFrame) -> None:
    st.subheader("⏱️ Salário Médio × Horas Contratadas por Sexo")

    gender_map = {
        "01": "Masculino",
        "02": "Feminino",
    }

    temp = data.copy()
    temp["sexo"] = temp["sexo"].map(gender_map).fillna(temp["sexo"])

    # Remover outliers de salário e horas
    limite_salario = temp["salario_mensal"].quantile(0.99)
    temp_filtered = temp[
        (temp["salario_mensal"] <= limite_salario) & 
        (temp["quantidade_horas_contratadas"] > 0) & 
        (temp["quantidade_horas_contratadas"] <= 44)
    ]
    
    # Condensar a informação: média salarial por horas contratadas e sexo
    condensed_data = (
        temp_filtered.groupby(["quantidade_horas_contratadas", "sexo"], as_index=False)
        .agg(salario_medio=("salario_mensal", "mean"))
    )

    fig = px.scatter(
        condensed_data,
        x="quantidade_horas_contratadas",
        y="salario_medio",
        color="sexo",
        trendline="ols",
        title="Correlação: Salário Médio por Horas Contratadas",
        labels={
            "quantidade_horas_contratadas": "Horas Contratadas",
            "salario_medio": "Salário Mensal Médio (R$)",
            "sexo": "Sexo"
        },
        color_discrete_map={"Masculino": "#1f77b4", "Feminino": "#e377c2"}
    )

    fig.update_layout(height=600)

    st.plotly_chart(fig, use_container_width=True)

def build_historical_pyramids(agg_data: pd.DataFrame) -> None:
    st.markdown("---")
    st.subheader("Evolução de Saldos Empregatícios para o biênio 2018 - 2019 no RS")

    temp = agg_data.copy()
    temp = temp[temp["faixa_salario"].isin(SALARY_RANGES)]

    def process_balance(df_year):
        admissions = df_year[df_year["admitidos_desligados"] == "01"].set_index("faixa_salario")["quantidade"]
        dismissals = df_year[df_year["admitidos_desligados"] == "02"].set_index("faixa_salario")["quantidade"]
        
        # Alinha as categorias e preenche NAs com 0
        df_bal = pd.DataFrame({"Admissões": admissions, "Desligamentos": dismissals}).fillna(0)
        df_bal["saldo"] = df_bal["Admissões"] - df_bal["Desligamentos"]
        df_bal = df_bal.reset_index()
        
        df_bal["faixa_salario"] = pd.Categorical(
            df_bal["faixa_salario"],
            categories=SALARY_RANGES,
            ordered=True,
        )
        return df_bal.sort_values("faixa_salario")

    cols = st.columns(2)
    years = [2018, 2019]

    for col, year in zip(cols, years):
        df_year = temp[temp["ano"] == year]
        if df_year.empty:
            continue
            
        balance_data = process_balance(df_year)

        fig_pyramid = px.bar(
            balance_data,
            x="saldo",
            y="faixa_salario",
            orientation="h",
            title=f"Saldo Admissões x Desligamentos - {year}",
            category_orders={"faixa_salario": SALARY_RANGES[::-1]},
            color="saldo",
            color_continuous_scale=px.colors.diverging.RdYlGn,
            color_continuous_midpoint=0
        )
        
        fig_pyramid.add_vline(x=0, line_dash="dash", line_color="#333333")
        
        fig_pyramid.update_layout(
            xaxis_title=None, 
            yaxis_title=None,
            coloraxis_showscale=False,
            margin=dict(l=0, r=0, t=30, b=0)
        )

        saldo = balance_data["saldo"].sum()
        
        with col:
            st.plotly_chart(fig_pyramid, use_container_width=True)
            st.metric(f"Saldo Total ({year})", f"{int(saldo):,}".replace(",", "."))

    st.markdown(
        "<p style='font-size: 24px; line-height: 1.6; margin-top: 20px; color: white; font-style: italic;'>"
        "Ao analisarmos o biênio 2018-2019, percebemos que há sempre um saldo geral positivo de empregos, o que frequentemente é divulgado como um indicador estritamente positivo. Porém, observa-se consistentemente uma forte diminuição de vagas nas faixas de salários maiores. Dessa forma, apesar do volume de empregos gerados estar em alta, a qualidade da renda da população via trabalho formal apresenta queda contínua no período.</p>",
        unsafe_allow_html=True
    )

def main() -> None:
    df = load_caged_dataset()
    df_agg = load_aggregated_dataset()

    monthly_avg = compute_monthly_average(df)
    gender_avg = compute_gender_average(df)
    pyramid_data = prepare_pyramid_data(df)

    build_metrics(df["salario_mensal"].mean())

    build_comparison_charts(
        monthly_avg,
        gender_avg,
    )

    build_pyramid_chart(pyramid_data)

    build_salary_vs_hours_chart(df)

    build_historical_pyramids(df_agg)

if __name__ == "__main__":
    main()