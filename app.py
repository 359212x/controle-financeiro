import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURAÇÃO VISUAL MODERNA ---
st.set_page_config(page_title="Finanças Familiares", layout="wide", initial_sidebar_state="collapsed")

# Estilização CSS para deixar o visual limpo e os botões destacados
st.markdown("""
    <style>
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        h1 { color: #1E3A8A; font-weight: 700; }
        h2 { color: #2563EB; }
        div[data-testid="stMetricValue"] { font-size: 1.8rem; font-weight: bold; color: #0F172A; }
        .stButton>button { border-radius: 6px; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Nosso Controle de Gastos")
st.markdown("---")

DESPESAS_FIXAS = [
    "COMBO CLARO", "SKY", "YOUTUBE PREMIUM", "GOOGLE GEMINI", "AMAZON", 
    "UNIMED JULINHA", "C6 TAG - PEDÁGIOS", "FAXINA", "ÁGUA", "LUZ", 
    "APAE", "CONSIGNADO", "MERCADO", "AÇOUGUE", "RESTAURANTES", "COMBUSTÍVEL"
]

# --- CONEXÃO BLINDADA COM CACHE ---
@st.cache_data(ttl=10)  # Atualiza a cada 10 segundos automaticamente ou sob comando
def carregar_dados_sheets():
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
            df_local = pd.DataFrame(dados)
            # Garante correspondência exata de colunas e limpa linhas vazias
            df_local = df_local.iloc[:, :5]
            df_local.columns = ["Data", "Tipo", "Descrição", "Valor", "Quem Pagou"]
            df_local["Valor"] = pd.to_numeric(df_local["Valor"], errors='coerce').fillna(0.0)
            return aba, df_local.reset_index(drop=True)
        else:
            df_vazio = pd.DataFrame(columns=["Data", "Tipo", "Descrição", "Valor", "Quem Pagou"])
            return aba, df_vazio
    except Exception as e:
        st.error(f"Erro ao conectar com a planilha: {e}")
        return None, pd.DataFrame(columns=["Data", "Tipo", "Descrição", "Valor", "Quem Pagou"])

# Força a leitura atualizada
aba, df = carregar_dados_sheets()

# --- FUNÇÃO DE SALVAMENTO RADICAL (SOBRESCREVE E LIMPA CACHE) ---
def salvar_df_na_nuvem(df_para_salvar):
    try:
        aba.clear()
        # Converte tudo para string/número padrão antes de enviar
        lista_dados = [["Data", "Tipo", "Descrição", "Valor", "Quem Pagou"]]
        for _, r in df_para_salvar.iterrows():
            lista_dados.append([str(r["Data"]), str(r["Tipo"]), str(r["Descrição"]), float(r["Valor"]), str(r["Quem Pagou"])])
        
        total_l = len(lista_dados)
        aba.update(range_name=f"A1:E{total_l}", values=lista_dados)
        
        # Destrói o cache antigo do Streamlit para forçar a releitura imediata do zero
        st.cache_data.clear()
        st.success("🔄 Alteração registrada com sucesso na nuvem!")
        st.rerun()
    except Exception as ex:
        st.error(f"Falha crítica ao gravar: {ex}")

# --- LAYOUT EM COLUNAS PRINCIPAIS (PAINEL DE CONTROLE) ---
col_esquerda, col_direita = st.columns([1, 2], gap="large")

# ==========================================
# COLUNA ESQUERDA: NOVO LANÇAMENTO & RESUMO
# ==========================================
with col_esquerda:
    st.subheader("📝 Registrar Novo Gasto")
    with st.form("novo_gasto_form", clear_on_submit=True):
        data = st.date_input("Data", datetime.now())
        tipo = st.selectbox("Tipo", ["Fixa", "Eventual"])
        
        if tipo == "Fixa":
            descricao = st.selectbox("Descrição (Fixa)", DESPESAS_FIXAS)
        else:
            descricao = st.text_input("Descrição (Eventual)", placeholder="Ex: Farmácia, Cinema...")
            
        valor = st.number_input("Valor (R$)", min_value=0.0, step=0.01, format="%.2f")
        pago_por = st.selectbox("Quem pagou?", ["Rodrigo", "Aline"])
        
        botao_inserir = st.form_submit_button("➕ Gravar Novo Gasto", use_container_width=True)
        
        if botao_inserir and valor > 0:
            novo_registro = pd.DataFrame([{
                "Data": data.strftime("%d/%m/%Y"),
                "Tipo": tipo,
                "Descrição": descricao,
                "Valor": valor,
                "Quem Pagou": pago_por
            }])
            df_atualizado = pd.concat([df, novo_registro], ignore_index=True)
            salvar_df_na_nuvem(df_atualizado)

    st.markdown("---")
    st.subheader("🧮 Fechamento de Contas")
    
    total_geral = df["Valor"].sum()
    total_rodrigo = df[df["Quem Pagou"] == "Rodrigo"]["Valor"].sum()
    total_aline = df[df["Quem Pagou"] == "Aline"]["Valor"].sum()
    
    st.metric("Gasto Total da Casa", f"R$ {total_geral:,.2f}")
    
    c_r, c_a = st.columns(2)
    c_r.metric("Rodrigo pagou", f"R$ {total_rodrigo:,.2f}")
    c_a.metric("Aline pagou", f"R$ {total_aline:,.2f}")
    
    metade = total_geral / 2
    if total_rodrigo > total_aline:
        st.warning(f"👉 **Aline** deve transferir **R$ {total_rodrigo - metade:,.2f}** para Rodrigo.")
    elif total_aline > total_rodrigo:
        st.warning(f"👉 **Rodrigo** deve transferir **R$ {total_aline - metade:,.2f}** para Aline.")
    else:
        st.success("🎉 Contas perfeitamente equilibradas!")

# ==========================================
# COLUNA DIREITA: HISTÓRICO & MODIFICAÇÃO
# ==========================================
with col_direita:
    st.subheader("📋 Lançamentos Registrados")
    
    if not df.empty:
        # Exibição visual limpa e elegante da tabela (estática, apenas para ver)
        df_view = df.copy()
        df_view["Valor"] = df_view["Valor"].map(lambda x: f"R$ {x:,.2f}")
        st.dataframe(df_view, use_container_width=True, height=280)
        
        st.markdown("---")
        st.subheader("⚙️ Painel de Modificação Direta")
        st.caption("Selecione um item abaixo para corrigir o valor ou apagá-lo instantaneamente.")
        
        # Cria um seletor amigável usando o índice do DataFrame
        opcoes = {i: f"Item {i+1}: {row['Data']} | {row['Descrição']} | R$ {row['Valor']:.2f} ({row['Quem Pagou']})" for i, row in df.iterrows()}
        idx_selecionado = st.selectbox("Escolha qual gasto deseja alterar:", options=list(opcoes.keys()), format_func=lambda x: opcoes[x])
        
        # Captura os dados do item que o usuário escolheu
        gasto_focado = df.iloc[idx_selecionado]
        
        with st.expander(f"✏️ Editar ou Apagar o Item {idx_selecionado + 1}", expanded=True):
            col_ed1, col_ed2 = st.columns(2)
            
            with col_ed1:
                # Modificação via caixas de texto independentes e seguras
                novo_val = st.number_input("Corrigir Valor (R$)", value=float(gasto_focado["Valor"]), step=0.01, format="%.2f", key="edit_val")
                novo_quem = st.selectbox("Corrigir Quem Pagou", ["Rodrigo", "Aline"], index=["Rodrigo", "Aline"].index(gasto_focado["Quem Pagou"]), key="edit_quem")
                
                if st.button("💾 Aplicar e Salvar Alteração", use_container_width=True, type="primary"):
                    df.at[idx_selecionado, "Valor"] = novo_val
                    df.at[idx_selecionado, "Quem Pagou"] = novo_quem
                    salvar_df_na_nuvem(df)
            
            with col_ed2:
                st.write("Ações de exclusão:")
                st.write("")
                if st.button("🗑️ APAGAR ESTE GASTO DEFINITIVAMENTE", use_container_width=True):
                    df_novo = df.drop(idx_selecionado).reset_index(drop=True)
                    salvar_df_na_nuvem(df_novo)
    else:
        st.info("Nenhum lançamento encontrado para este mês.")
