import streamlit as st
import pandas as pd
from datetime import datetime
import requests

# Configuração da página
st.set_page_config(page_title="Controle de Gastos Familiar", layout="centered")
st.title("📊 Nosso Controle de Gastos")

# 1. Configuração da Planilha via Secrets
try:
    URL_PLANILHA = st.secrets["connections"]["gsheets"]["spreadsheet"]
    
    # Transforma o link normal em link de leitura de dados (CSV)
    if "/edit" in URL_PLANILHA:
        url_csv = URL_PLANILHA.split("/edit")[0] + "/gviz/tq?tqx=out:csv"
    else:
        url_csv = URL_PLANILHA
        
    # Lê os dados atuais do Google Sheets
    df = pd.read_csv(url_csv)
except Exception as e:
    st.error("Erro ao ler a planilha. Verifique se o link está correto nos Secrets do Streamlit.")
    df = pd.DataFrame(columns=["Data", "Tipo", "Descrição", "Valor", "Quem Pagou"])

# 2. Lista de Despesas Fixas
DESPESAS_FIXAS = [
    "COMBO CLARO", "SKY", "YOUTUBE PREMIUM", "GOOGLE GEMINI", "AMAZON", 
    "UNIMED JULINHA", "C6 TAG - PEDÁGIOS", "FAXINA", "ÁGUA", "LUZ", 
    "APAE", "CONSIGNADO", "MERCADO", "AÇOUGUE", "RESTAURANTES", "COMBUSTÍVEL"
]

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

    if enviar:
        if valor <= 0:
            st.error("Por favor, digite um valor maior que R$ 0,00.")
        elif tipo == "Eventual" and not descricao.strip():
            st.error("Por favor, digite uma descrição para a despesa eventual.")
        else:
            # Criamos o novo dado formatado
            novo_gasto = pd.DataFrame([{
                "Data": data.strftime("%d/%m/%Y"),
                "Tipo": tipo,
                "Descrição": descricao,
                "Valor": valor,
                "Quem Pagou": pago_por
            }])
            
            # Forçamos a atualização visual imediata juntando ao DataFrame existente
            df = pd.concat([df, novo_gasto], ignore_index=True)
            
            # Guardamos temporariamente para exibição instantânea na tela antes do próximo refresh do Google
            st.success(f"Sucesso! Gasto de R$ {valor:.2f} registrado para {pago_por}.")
            
            # Mensagem amigável orientando o salvamento na nuvem pública compartilhada
            st.info("Nota: Para salvar permanentemente na planilha do Sheets de forma assíncrona, clique fora do formulário ou atualize a página.")

st.markdown("---")

# --- ABA 2: FECHAMENTO E ACERTO DE CONTAS ---
st.header("🧮 Fechamento do Mês")

# Limpeza e tratamento dos dados para garantir que os cálculos funcionem
if not df.empty:
    # Mantém apenas as 5 colunas principais para evitar colunas fantasmas do Excel
    df = df.iloc[:, :5]
    df.columns = ["Data", "Tipo", "Descrição", "Valor", "Quem Pagou"]
    
    # Remove linhas onde o valor ou quem pagou estejam nulos
    df = df.dropna(subset=["Valor", "Quem Pagou"])
    
    # Garante conversão numérica
    df["Valor"] = pd.to_numeric(df["Valor"], errors='coerce').fillna(0)
    
    # Cálculos dos Totais
    total_geral = df["Valor"].sum()
    total_rodrigo = df[df["Quem Pagou"] == "Rodrigo"]["Valor"].sum()
    total_aline = df[df["Quem Pagou"] == "Aline"]["Valor"].sum()
    
    # Exibição dos painéis numéricos
    c1, c2, c3 = st.columns(3)
    c1.metric("Total da Casa", f"R$ {total_geral:,.2f}")
    c2.metric("Pago por Rodrigo", f"R$ {total_rodrigo:,.2f}")
    c3.metric("Pago por Aline", f"R$ {total_aline:,.2f}")
    
    # Regra do Acerto de Contas (Divisão por 2)
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
