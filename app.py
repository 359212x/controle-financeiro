import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# Configuração da página
st.set_page_config(page_title="Controle de Gastos Familiar", layout="centered")
st.title("📊 Nosso Controle de Gastos")

# Lista de Despesas Fixas
DESPESAS_FIXAS = [
    "COMBO CLARO", "SKY", "YOUTUBE PREMIUM", "GOOGLE GEMINI", "AMAZON", 
    "UNIMED JULINHA", "C6 TAG - PEDÁGIOS", "FAXINA", "ÁGUA", "LUZ", 
    "APAE", "CONSIGNADO", "MERCADO", "AÇOUGUE", "RESTAURANTES", "COMBUSTÍVEL"
]

# Autenticação oficial com o Google Sheets usando os Secrets
try:
    escopos = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    info_chave = dict(st.secrets["gcp_service_account"])
    credenciais = Credentials.from_service_account_info(info_chave, scopes=escopos)
    gc = gspread.authorize(credenciais)
    
    URL_PLANILHA = st.secrets["connections"]["gsheets"]["spreadsheet"]
    planilha = gc.open_by_url(URL_PLANILHA)
    aba = planilha.get_worksheet(0)
    
    # Leitura em tempo real dos dados na planilha
    dados_tabela = aba.get_all_records()
    if dados_tabela:
        df = pd.DataFrame(dados_tabela)
    else:
        df = pd.DataFrame(columns=["Data", "Tipo", "Descrição", "Valor", "Quem Pagou"])
except Exception as e:
    st.error("Erro na conexão segura com o Google Sheets. Verifique as chaves nos Secrets.")
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
        # Cria a lista exatamente na ordem das colunas da planilha
        nova_linha = [data.strftime("%d/%m/%Y"), tipo, descricao, valor, pago_por]
        
        try:
            # Gravação em tempo real direto na planilha do Google!
            aba.append_row(nova_linha)
            st.success(f"Gasto de R$ {valor:.2f} gravado permanentemente no Google Sheets!")
            st.rerun()
        except Exception as erro:
            st.error(f"Falha ao gravar os dados: {erro}")

st.markdown("---")

# --- ABA 2: FECHAMENTO E ACERTO DE CONTAS ---
st.header("🧮 Fechamento do Mês")

if not df.empty:
    df = df.iloc[:, :5]
    df.columns = ["Data", "Tipo", "Descrição", "Valor", "Quem Pagou"]
    df = df.dropna(subset=["Valor"])
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
    st.info("Nenhum gasto localizado na planilha para este mês.")
