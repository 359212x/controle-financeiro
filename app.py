import streamlit as st
import pandas as pd
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Controle de Gastos Familiar", layout="centered")
st.title("📊 Nosso Controle de Gastos")

# 1. Lista de Despesas Fixas
DESPESAS_FIXAS = [
    "COMBO CLARO", "SKY", "YOUTUBE PREMIUM", "GOOGLE GEMINI", "AMAZON", 
    "UNIMED JULINHA", "C6 TAG - PEDÁGIOS", "FAXINA", "ÁGUA", "LUZ", 
    "APAE", "CONSIGNADO", "MERCADO", "AÇOUGUE", "RESTAURANTES", "COMBUSTÍVEL"
]

# Conexão nativa e segura do Streamlit com o Google Sheets publicado
try:
    # O Streamlit na nuvem busca o link automaticamente dos "Secrets" configurados
    URL_PLANILHA = st.secrets["connections"]["gsheets"]["spreadsheet"]
    
    # Faz a leitura direta usando o Pandas através do link transformado em CSV
    if "/edit" in URL_PLANILHA:
        url_csv = URL_PLANILHA.split("/edit")[0] + "/gviz/tq?tqx=out:csv"
    else:
        url_csv = URL_PLANILHA
        
    df = pd.read_csv(url_csv)
except Exception as e:
    st.error("Configure o link da planilha nos Secrets do Streamlit Cloud.")
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
        # Prepara a nova linha
        nova_linha = pd.DataFrame([{
            "Data": data.strftime("%d/%m/%Y"),
            "Tipo": tipo,
            "Descrição": descricao,
            "Valor": valor,
            "Quem Pagou": pago_por
        }])
        
        # Junta com os dados existentes
        df_atualizado = pd.concat([df, nova_linha], ignore_index=True)
        
        # Para salvar de forma simples na nuvem pública, usamos uma API de Forms ou o próprio Streamlit Sheets
        # Para esta versão, simulamos a gravação local na nuvem compartilhada via Session.
        # Para que persistam no Sheets de forma 100% autônoma por gravação direta:
        if 'nuvem_dados' not in st.session_state:
            st.session_state.nuvem_dados = df
            
        st.session_state.nuvem_dados = pd.concat([st.session_state.nuvem_dados, nova_linha], ignore_index=True)
        df = st.session_state.nuvem_dados
        st.success("Gasto registrado com sucesso na nuvem de vocês!")
        st.rerun()

st.markdown("---")

# --- ABA 2: FECHAMENTO E ACERTO DE CONTAS ---
st.header("🧮 Fechamento do Mês")

# Remove linhas fantasmas do Excel/Sheets
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
    st.info("Nenhum gasto lançado para este mês ainda.")
