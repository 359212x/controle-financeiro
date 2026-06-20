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
    
    # Leitura dos dados
    dados_tabela = aba.get_all_records()
    if dados_tabela:
        df = pd.DataFrame(dados_tabela)
    else:
        df = pd.DataFrame(columns=["Data", "Tipo", "Descrição", "Valor", "Quem Pagou"])
except Exception as e:
    st.error("Erro na conexão segura com o Google Sheets. Verifique as chaves nos Secrets.")
    df = pd.DataFrame(columns=["Data", "Tipo", "Descrição", "Valor", "Quem Pagou"])

# Criação de abas para organizar o aplicativo
aba_lancamento, aba_gerenciamento = st.tabs(["📝 Novo Lançamento", "⚙️ Histórico & Fechamento"])

# --- ABA 1: NOVO LANÇAMENTO ---
with aba_lancamento:
    st.header("Registrar Novo Gasto")
    with st.form("formulario_gasto", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            data = st.date_input("Data do Gasto", datetime.now(), key="nova_data")
            tipo = st.selectbox("Tipo de Despesa", ["Fixa", "Eventual"], key="novo_tipo")
        with col2:
            pago_por = st.selectbox("Quem pagou?", ["Rodrigo", "Aline"], key="novo_pago")
            valor = st.number_input("Valor (R$)", min_value=0.0, step=0.01, format="%.2f", key="novo_valor")
        
        if tipo == "Fixa":
            descricao = st.selectbox("Selecione a Despesa Fixa", DESPESAS_FIXAS, key="nova_desc_fixa")
        else:
            descricao = st.text_input("Descrição da Despesa Eventual", key="nova_desc_eve")

        enviar = st.form_submit_button("Salvar Lançamento")

        if enviar and valor > 0:
            nova_linha = [data.strftime("%d/%m/%Y"), tipo, descricao, valor, pago_por]
            try:
                aba.append_row(nova_linha)
                st.success(f"Gasto de R$ {valor:,.2f} gravado com sucesso!")
                st.rerun()
            except Exception as erro:
                st.error(f"Falha ao gravar os dados: {erro}")

# --- ABA 2: FECHAMENTO E EDIÇÃO DIRETA ---
with aba_gerenciamento:
    st.header("🧮 Fechamento e Histórico")
    
    if not df.empty:
        df = df.iloc[:, :5]
        df.columns = ["Data", "Tipo", "Descrição", "Valor", "Quem Pagou"]
        df = df.dropna(subset=["Valor"])
        
        df["Valor"] = pd.to_numeric(df["Valor"], errors='coerce').fillna(0)
        df = df.reset_index(drop=True)
        
        # Cálculos e Cards de Resumo
        total_geral = df["Valor"].sum()
        total_rodrigo = df[df["Quem Pagou"] == "Rodrigo"]["Valor"].sum()
        total_aline = df[df["Quem Pagou"] == "Aline"]["Valor"].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total da Casa", f"R$ {total_geral:,.2f}")
        c2.metric("Pago por Rodrigo", f"R$ {total_rodrigo:,.2f}")
        c3.metric("Pago por Aline", f"R$ {total_aline:,.2f}")
        
        metade_ideal = total_geral / 2
        
        if total_rodrigo > total_aline:
            st.info(f"**Aline** deve fazer um Pix de **R$ {total_rodrigo - metade_ideal:,.2f}** para **Rodrigo**.")
        elif total_aline > total_rodrigo:
            st.info(f"**Rodrigo** deve fazer um Pix de **R$ {total_aline - metade_ideal:,.2f}** para **Aline**.")
        else:
            st.success("Contas equilibradas!")
            
        st.markdown("---")
        st.subheader("📋 Planilha de Lançamentos (Clique para Editar ou Excluir)")
        st.caption("Dê duplo clique em qualquer célula para alterar. A coluna de Valor aceita qualquer digitação livre (usando vírgula).")
        
        # Prepara exibição visual com a vírgula para ficar amigável
        df_visual = df.copy()
        df_visual["Valor"] = df_visual["Valor"].map(lambda x: f"{x:.2f}".replace(".", ","))
        
        tabela_editada = st.data_editor(
            df_visual,
            key="editor_principal_gastos_v4",
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "Quem Pagou": st.column_config.SelectboxColumn(options=["Rodrigo", "Aline"]),
                "Tipo": st.column_config.SelectboxColumn(options=["Fixa", "Eventual"]),
                "Valor": st.column_config.TextColumn(label="Valor (R$)")
            }
        )
        
        if st.button("💾 SALVAR ALTERAÇÕES DA TABELA", use_container_width=True, type="primary"):
            try:
                lista_linhas = tabela_editada.values.tolist()
                
                # Processa os dados limpando a pontuação e convertendo para número puro
                lista_processada = []
                for linha in lista_linhas:
                    data_l, tipo_l, desc_l, val_texto, quem_l = linha
                    try:
                        val_limpo = str(val_texto).replace("R$", "").replace(".", "").replace(",", ".").strip()
                        val_numerico = float(val_limpo)
                    except ValueError:
                        val_numerico = 0.0
                        
                    lista_processada.append([data_l, tipo_l, desc_l, val_numerico, quem_l])
                
                # CORREÇÃO DEFINITIVA: Recria os cabeçalhos manualmente em formato de texto para evitar que o Streamlit quebre a tabela
                cabecalhos = [["Data", "Tipo", "Descrição", "Valor", "Quem Pagou"]]
                corpo_tabela = cabecalhos + lista_processada
                
                # Descobre o intervalo exato ocupado pela tabela (ex: A1:E15)
                total_linhas = len(corpo_tabela)
                intervalo_atualizacao = f"A1:E{total_linhas}"
                
                # Limpa os registros antigos e escreve os novos de forma blindada
                aba.clear()
                aba.update(range_name=intervalo_atualizacao, values=corpo_tabela)
                
                st.success("Alterações salvas permanentemente na nuvem!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao salvar alterações: {e}")
                
    else:
        st.info("Nenhum gasto localizado na planilha para este mês.")
