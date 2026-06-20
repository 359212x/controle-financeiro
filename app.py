import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import time

# --- CONFIGURAÇÃO DE LAYOUT CLEAN ---
st.set_page_config(page_title="Controle Financeiro", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        .block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 600px; }
        h1 { color: #1E293B; font-weight: 700; font-size: 1.8rem; margin-bottom: 1.5rem; text-align: center; }
        h3 { color: #334155; font-weight: 600; font-size: 1.2rem; margin-top: 1.5rem; margin-bottom: 0.8rem; }
        div[data-testid="stMetricValue"] { font-size: 1.6rem; font-weight: 700; color: #0F172A; }
        .stButton>button { border-radius: 8px; font-weight: 600; height: 3rem; }
        .stForm { border-radius: 12px; border: 1px solid #E2E8F0; padding: 1.5rem; background-color: #F8FAFC; }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Nosso Controle de Gastos")

DESPESAS_FIXAS = [
    "COMBO CLARO", "SKY", "YOUTUBE PREMIUM", "GOOGLE GEMINI", "AMAZON", 
    "UNIMED JULINHA", "C6 TAG - PEDÁGIOS", "FAXINA", "ÁGUA", "LUZ", 
    "APAE", "CONSIGNADO", "MERCADO", "AÇOUGUE", "RESTAURANTES", "COMBUSTÍVEL"
]

# --- CONEXÃO DIRETA SEM CACHE ---
try:
    escopos = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    info_chave = dict(st.secrets["gcp_service_account"])
    credenciais = Credentials.from_service_account_info(info_chave, scopes=escopos)
    gc = gspread.authorize(credenciais)
    
    URL_PLANILHA = st.secrets["connections"]["gsheets"]["spreadsheet"]
    planilha = gc.open_by_url(URL_PLANILHA)
    aba = planilha.get_worksheet(0)
    
    dados = aba.get_all_records()
    if dados:
        df = pd.DataFrame(dados).iloc[:, :5]
        df.columns = ["Data", "Tipo", "Descrição", "Valor", "Quem Pagou"]
        df["Valor"] = pd.to_numeric(df["Valor"], errors='coerce').fillna(0.0)
        df = df.reset_index(drop=True)
    else:
        df = pd.DataFrame(columns=["Data", "Tipo", "Descrição", "Valor", "Quem Pagou"])
except Exception as e:
    st.error(f"⚠️ Erro de conexão com o Google Sheets: {e}")
    df = pd.DataFrame(columns=["Data", "Tipo", "Descrição", "Valor", "Quem Pagou"])


# --- FUNÇÃO ATUALIZADORA BLINDADA ---
def salvar_lista_na_nuvem(lista_dados):
    try:
        aba.clear()
        time.sleep(0.5) # Pausa técnica para o Google registrar o esvaziamento
        total_l = len(lista_dados)
        aba.update(range_name=f"A1:E{total_l}", values=lista_dados)
        st.success("🔄 Alteração salva com sucesso!")
        time.sleep(0.5)
        st.rerun()
    except Exception as ex:
        st.error(f"Erro ao salvar: {ex}")


# ==========================================
# SEÇÃO 1: RESUMO FINANCEIRO & FECHAMENTO
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
        st.success("🎉 Contas perfeitamente equilibradas!")

st.markdown("---")

# ==========================================
# SEÇÃO 2: ADICIONAR NOVO GASTO
# ==========================================
st.subheader("📝 Novo Lançamento")
with st.form("novo_gasto_form", clear_on_submit=True):
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        data = st.date_input("Data", datetime.now())
        tipo = st.selectbox("Tipo", ["Fixa", "Eventual"])
    with col_f2:
        valor = st.number_input("Valor (R$)", min_value=0.0, step=0.01, format="%.2f")
        pago_por = st.selectbox("Quem pagou?", ["Rodrigo", "Aline"])
    
    if tipo == "Fixa":
        descricao = st.selectbox("Selecione a Despesa Fixa", DESPESAS_FIXAS)
    else:
        descricao = st.text_input("Descrição do Gasto Eventual", placeholder="Ex: Farmácia...")
        
    botao_inserir = st.form_submit_button("Salvar Lançamento", use_container_width=True, type="primary")
    
    if botao_inserir and valor > 0:
        cabecalhos = [["Data", "Tipo", "Descrição", "Valor", "Quem Pagou"]]
        lista_atual = []
        for _, r in df.iterrows():
            lista_atual.append([str(r["Data"]), str(r["Tipo"]), str(r["Descrição"]), float(r["Valor"]), str(r["Quem Pagou"])])
        
        lista_atual.append([data.strftime("%d/%m/%Y"), tipo, descricao, float(valor), pago_por])
        salvar_lista_na_nuvem(cabecalhos + lista_atual)

st.markdown("---")

# ==========================================
# SEÇÃO 3: HISTÓRICO & MODIFICAÇÃO
# ==========================================
st.subheader("📋 Histórico de Lançamentos")

if not df.empty:
    df_view = df.copy()
    df_view["Valor"] = df_view["Valor"].map(lambda x: f"R$ {x:,.2f}")
    st.dataframe(df_view, use_container_width=True, height=240)
    
    st.write("")
    opcoes = {i: f"Item {i+1}: {row['Descrição']} — R$ {row['Valor']:.2f} ({row['Quem Pagou']})" for i, row in df.iterrows()}
    idx_selecionado = st.selectbox("Selecione um item caso queira Alterar ou Excluir:", options=list(opcoes.keys()), format_func=lambda x: opcoes[x])
    
    gasto_focado = df.iloc[idx_selecionado]
    
    with st.expander("🛠️ Painel de Ajuste do Item Selecionado", expanded=False):
        col_ed1, col_ed2 = st.columns(2)
        with col_ed1:
            novo_val = st.number_input("Corrigir Valor", value=float(gasto_focado["Valor"]), step=0.01, format="%.2f", key="ed_val_input")
            novo_quem = st.selectbox("Corrigir Quem Pagou", ["Rodrigo", "Aline"], index=["Rodrigo", "Aline"].index(gasto_focado["Quem Pagou"]), key="ed_quem_input")
            
            if st.button("💾 Gravar Correção", use_container_width=True):
                cabecalhos = [["Data", "Tipo", "Descrição", "Valor", "Quem Pagou"]]
                lista_nova = []
                for idx, r in df.iterrows():
                    if idx == idx_selecionado:
                        # Força explicitamente a conversão do input numérico para float puro
                        lista_nova.append([str(r["Data"]), str(r["Tipo"]), str(r["Descrição"]), float(novo_val), str(novo_quem)])
                    else:
                        lista_nova.append([str(r["Data"]), str(r["Tipo"]), str(r["Descrição"]), float(r["Valor"]), str(r["Quem Pagou"])])
                
                salvar_lista_na_nuvem(cabecalhos + lista_nova)
        
        with col_ed2:
            st.write("Ação irreversível:")
            st.write("")
            if st.button("🗑️ Deletar Lançamento", use_container_width=True, type="secondary"):
                cabecalhos = [["Data", "Tipo", "Descrição", "Valor", "Quem Pagou"]]
                lista_nova = []
                for idx, r in df.iterrows():
                    if idx != idx_selecionado:
                        lista_nova.append([str(r["Data"]), str(r["Tipo"]), str(r["Descrição"]), float(r["Valor"]), str(r["Quem Pagou"])])
                
                salvar_lista_na_nuvem(cabecalhos + lista_nova)
else:
    st.info("Nenhum lançamento localizado para este mês.")
