import streamlit as st
import pandas as pd
from datetime import datetime
import requests

# Configuração da página
st.set_page_config(page_title="Controle de Gastos Familiar", layout="centered")
st.title("📊 Nosso Controle de Gastos")

# COLE O LINK DA SUA PLANILHA AQUI DENTRO DAS ASPAS:
URL_DA_PLANILHA = "https://docs.google.com/spreadsheets/d/1rvNSHh7ircJYLti8T0NzRFOp8tkTTDxxcfMHz6KdOX0/edit?usp=sharing"

# 1. Lista de Despesas Fixas
DESPESAS_FIXAS = [
    "COMBO CLARO", "SKY", "YOUTUBE PREMIUM", "GOOGLE GEMINI", "AMAZON", 
    "UNIMED JULINHA", "C6 TAG - PEDÁGIOS", "FAXINA", "ÁGUA", "LUZ", 
    "APAE", "CONSIGNADO", "MERCADO", "AÇOUGUE", "RESTAURANTES", "COMBUSTÍVEL"
]

# Função para transformar o link normal em link de leitura de dados
def obter_link_csv(url):
    if "/edit" in url:
        return url.split("/edit")[0] + "/gviz/tq?tqx=out:csv"
    return url

# Leitura dos dados usando uma requisição web simples
try:
    url_csv = obter_link_csv(URL_DA_PLANILHA)
    df = pd.read_csv(url_csv)
    # Garante que as colunas necessárias existem se a planilha estiver vazia
    if df.empty and len(df.columns) < 5:
        df = pd.DataFrame(columns=["Data", "Tipo", "Descrição", "Valor", "Quem Pagou"])
except Exception as e:
    st.error("Erro ao ler os dados da planilha. Certifique-se de que o link está correto e compartilhado como 'Qualquer pessoa com o link pode editar'.")
    df = pd.DataFrame(columns=["Data", "Tipo", "Descrição", "Valor", "Quem Pagou"])

# --- ABA 1: NOVO LANÇAMENTO ---
st.header("📝 Registrar Novo Gasto")

with st.form("formulario_gasto", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        data = st.date_input("Data do Gasto", datetime.now())
        tipo = st.selectbox("Tipo de Despesa", ["Fixa", "Eventual"])
    with col2:
        pago_por = st.selectbox("Quem pagou?", ["Rodrigo", "Aline"])
        valor = st.number_input("Valor (R$)", min_value=0.0, step=10.0, format="%.2f")
    
    if tipo == "Fixa":
        descricao = st.selectbox("Selecione a Despesa Fixa", DESPESAS_FIXAS)
    else:
        descricao = st.text_input("Descrição da Despesa Eventual (ex: Manutenção Máquina)")

    enviar = st.form_submit_button("Salvar Lançamento")

    if enviar and valor > 0:
        # Prepara os dados para enviar via formulário web estruturado do Google (Form)
        # Como o Sheets puro bloqueia escrita externa anônima, a melhor alternativa 
        # local antes de ir para a nuvem é simular o append no DataFrame para visualização provisória:
        st.warning("Para salvar de forma permanente na nuvem acessível por múltiplos dispositivos, precisamos publicar o app no Streamlit Cloud. O teste local simula o envio abaixo:")
        
        novo_gasto = pd.DataFrame([{
            "Data": data.strftime("%d/%m/%Y"),
            "Tipo": tipo,
            "Descrição": descricao,
            "Valor": valor,
            "Quem Pagou": pago_por
        }])
        df = pd.concat([df, novo_gasto], ignore_index=True)
        st.success("Gasto registrado com sucesso nesta sessão!")

st.markdown("---")

# --- ABA 2: FECHAMENTO E ACERTO DE CONTAS ---
st.header("🧮 Fechamento do Mês")

# Limpeza de colunas fantasmas que o Google Sheets às vezes gera
df = df.iloc[:, :5]
df.columns = ["Data", "Tipo", "Descrição", "Valor", "Quem Pagou"]
df = df.dropna(subset=["Valor"])

if not df.empty:
    df["Valor"] = pd.to_numeric(df["Valor"], errors='coerce').fillna(0)
    
    total_geral = df["Valor"].sum()
    total_rodrigo = df[df["Quem Pagou"] == "Rodrigo"]["Valor"].sum()
    total_aline = df[df["Quem Pagou"] == "Aline"]["Valor"].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total da Casa", f"R$ {total_geral:,.2f}")
    c2.metric("Pago por Rodrigo", f"R$ {total_rodrigo:,.2f}")
    c3.metric("Pago por Aline", f"R$ {total_aline:,.2f}")
    
    metade_ideal = total_geral / 2
    
    st.subheader("🔄 Resultado do Acerto")
    if total_rodrigo > total_aline:
        diferenca = total_rodrigo - metade_ideal
        st.info(f"**Aline** deve fazer um Pix de **R$ {diferenca:,.2f}** para **Rodrigo**.")
    elif total_aline > total_rodrigo:
        diferenca = total_aline - metade_ideal
        st.info(f"**Rodrigo** deve fazer um Pix de **R$ {diferenca:,.2f}** para **Aline**.")
    else:
        st.success("Contas perfeitamente equilibradas! Ninguém deve nada.")
        
    st.subheader("📋 Histórico de Lançamentos")
    st.dataframe(df, use_container_width=True)
else:
    st.info("Nenhum gasto lançado para este mês ainda.")