import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import time

# --- CONFIGURAÇÃO VISUAL PROFISSIONAL & CLEAN ---
st.set_page_config(page_title="Finanças da Casa", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        .block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 550px; }
        h1 { color: #0F172A; font-weight: 800; font-size: 1.8rem; margin-bottom: 1.5rem; text-align: center; letter-spacing: -0.5px; }
        h3 { color: #334155; font-weight: 600; font-size: 1.15rem; margin-top: 1.5rem; margin-bottom: 0.6rem; }
        div[data-testid="stMetricValue"] { font-size: 1.5rem; font-weight: 700; color: #0F172A; }
        .stButton>button { border-radius: 8px; font-weight: 600; height: 3rem; }
        .stForm { border-radius: 12px; border: 1px solid #E2E8F0; padding: 1.5rem; background-color: #F8FAFC; box-shadow: 0 1px 3px rgba(0,0,0,0.02); }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Nosso Controle de Gastos")

DESPESAS_FIXAS = [
    "COMBO CLARO", "SKY", "YOUTUBE PREMIUM", "GOOGLE GEMINI", "AMAZON", 
    "UNIMED JULINHA", "C6 TAG - PEDÁGIOS", "FAXINA", "ÁGUA", "LUZ", 
    "APAE", "CONSIGNADO", "MERCADO", "AÇOUGUE", "RESTAURANTES", "COMBUSTÍVEL"
]

# --- CONEXÃO DIRETA E RESILIENTE ---
try:
    escopos = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    info_chave = dict(st.secrets["gcp_service_account"])
    credenciais = Credentials.from_service_account_info(info_chave, scopes=escopos)
    gc = gspread.authorize(credenciais)
    
    URL_PLANILHA = st.secrets["connections"]["gsheets"]["spreadsheet"]
    planilha = gc.open_by_url(URL_PLANILHA)
    aba = planilha.get_worksheet(0)
    
    # Baixa os dados brutos mantendo a numeração da linha do Sheets
    dados_brutos = aba.get_all_values()
    
    if len(dados_brutos) > 1:
        # Monta o DataFrame guardando o número real da linha (index original + 2)
        linhas = []
        for i, r in enumerate(dados_brutos[1:]):
            # Preenche colunas vazias caso falte alguma coisa na planilha
            while len(r) < 5:
                r.append("")
            linhas.append({
                "LinhaPlanilha": i + 2, # Linha 1 são os cabeçalhos
                "Data": str(r[0]),
                "Tipo": str(r[1]),
                "Descrição": str(r[2]),
                "Valor": pd.to_numeric(str(r[3]).replace("R$", "").replace(".", "").replace(",", ".").strip(), errors='coerce') or 0.0,
                "Quem Pagou": str(r[4])
            })
        df = pd.DataFrame(linhas)
    else:
        df = pd.DataFrame(columns=["LinhaPlanilha", "Data", "Tipo", "Descrição", "Valor", "Quem Pagou"])
except Exception as e:
    st.error(f"⚠️ Falha de sincronização com o Sheets: {e}")
    df = pd.DataFrame(columns=["LinhaPlanilha", "Data", "Tipo", "Descrição", "Valor", "Quem Pagou"])


# ==========================================
# SEÇÃO 1: PAINEL DE RESUMO (KPIs)
# ==========================================
total_geral = df["Valor"].sum() if not df.empty else 0.0
total_rodrigo = df[df["Quem Pagou"] == "Rodrigo"]["Valor"].sum() if not df.empty else 0.0
total_aline = df[df["Quem Pagou"] == "Aline"]["Valor"].sum() if not df.empty else 0.0

with st.container():
    c1, c2, c3 = st.columns(3)
    c1.metric("Total da Casa", f"R$ {total_geral:,.2f}")
    c2.metric("Rodrigo", f"R$ {total_rodrigo:,.2f}")
    c3.metric("Aline", f"R$ {total_aline:,.2f}")
    
    metade = total_geral / 2
    if total_rodrigo > total_aline:
        st.info(f"💡 **Aline** transfere **R$ {total_rodrigo - metade:,.2f}** para Rodrigo.")
    elif total_aline > total_rodrigo:
        st.info(f"💡 **Rodrigo** transfere **R$ {total_aline - metade:,.2f}** para Aline.")
    elif total_geral > 0:
        st.success("🎉 Contas equilibradas!")

st.markdown("---")

# ==========================================
# SEÇÃO 2: ADICIONAR NOVO LANÇAMENTO
# ==========================================
st.subheader("📝 Novo Lançamento")
with st.form("novo_gasto_form", clear_on_submit=True):
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        data_input = st.date_input("Data", datetime.now())
        tipo_input = st.selectbox("Tipo", ["Fixa", "Eventual"])
    with col_f2:
        valor_input = st.number_input("Valor (R$)", min_value=0.0, step=0.01, format="%.2f")
        pago_input = st.selectbox("Quem pagou?", ["Rodrigo", "Aline"])
    
    if tipo_input == "Fixa":
        desc_input = st.selectbox("Selecione a Despesa Fixa", DESPESAS_FIXAS)
    else:
        desc_input = st.text_input("Descrição do Gasto Eventual", placeholder="Ex: Farmácia, PetShop...")
        
    botao_inserir = st.form_submit_button("Salvar na Planilha", use_container_width=True, type="primary")
    
    if botao_inserir and valor_input > 0:
        try:
            nova_linha = [data_input.strftime("%d/%m/%Y"), tipo_input, desc_input, float(valor_input), pago_input]
            aba.append_row(nova_linha)
            st.success("✅ Adicionado com sucesso!")
            time.sleep(0.4)
            st.rerun()
        except Exception as err:
            st.error(f"Erro ao inserir: {err}")

st.markdown("---")

# ==========================================
# SEÇÃO 3: HISTÓRICO, EDIÇÃO & EXCLUSÃO
# ==========================================
st.subheader("📋 Histórico & Alterações")

if not df.empty:
    # Exibição visual limpa da tabela
    df_visual = df.copy()
    df_visual["Valor"] = df_visual["Valor"].map(lambda x: f"R$ {x:,.2f}")
    st.dataframe(df_visual.drop(columns=["LinhaPlanilha"]), use_container_width=True, height=220)
    
    st.write("")
    # Menu seletor indexado de forma amigável
    opcoes_gastos = {
        row["LinhaPlanilha"]: f"Linha {idx+1}: {row['Descrição']} — R$ {row['Valor']:.2f} ({row['Quem Pagou']})" 
        for idx, row in df.iterrows()
    }
    
    linha_selecionada = st.selectbox(
        "Selecione um item para Modificar ou Excluir:", 
        options=list(opcoes_gastos.keys()), 
        format_func=lambda x: opcoes_gastos[x]
    )
    
    gasto_selecionado = df[df["LinhaPlanilha"] == row_to_edit if 'row_to_edit' in locals() else df["LinhaPlanilha"] == linha_selecionada].iloc[0]
    
    # Painel expander minimalista para alteração rápida
    with st.expander("🛠️ Editar ou Remover o Item Selecionado", expanded=False):
        col_ed1, col_ed2 = st.columns(2)
        
        with col_ed1:
            novo_valor = st.number_input("Corrigir Valor (R$)", value=float(gasto_selecionado["Valor"]), step=0.01, format="%.2f", key="edit_val")
            novo_pagador = st.selectbox("Corrigir Quem Pagou", ["Rodrigo", "Aline"], index=["Rodrigo", "Aline"].index(gasto_selecionado["Quem Pagou"]), key="edit_quem")
            
            if st.button("💾 Gravar Correção", use_container_width=True):
                try:
                    # ATUALIZAÇÃO CIRÚRGICA: Modifica diretamente a célula daquela linha na Nuvem
                    num_linha = int(gasto_selecionado["LinhaPlanilha"])
                    aba.update_cell(num_linha, 4, float(novo_valor))     # Coluna D: Valor
                    aba.update_cell(num_linha, 5, str(novo_pagador))     # Coluna E: Quem Pagou
                    st.success("🔄 Registro corrigido e salvo no Sheets!")
                    time.sleep(0.5)
                    st.rerun()
                except Exception as ex_edit:
                    st.error(f"Falha ao editar célula: {ex_edit}")
                    
        with col_ed2:
            st.write("Excluir definitivamente:")
            st.write("")
            if st.button("🗑️ Deletar Lançamento", use_container_width=True, type="secondary"):
                try:
                    num_linha = int(gasto_selecionado["LinhaPlanilha"])
                    aba.delete_rows(num_linha)
                    st.success("🗑️ Item removido da planilha!")
                    time.sleep(0.5)
                    st.rerun()
                except Exception as ex_del:
                    st.error(f"Falha ao deletar: {ex_del}")
else:
    st.info("Nenhum lançamento localizado nesta planilha.")
