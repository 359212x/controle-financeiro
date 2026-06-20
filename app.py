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

# --- ABA 2: FECHAMENTO, ALTERAÇÃO E EXCLUSÃO SÓLIDA ---
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
        st.subheader("⚙️ Painel de Modificação e Exclusão")
        
        opcoes_selecao = []
        for idx, linha in df.iterrows():
            opcoes_selecao.append(f"Linha {idx + 2}: {linha['Data']} - {linha['Descrição']} (R$ {linha['Valor']:.2f})")
            
        item_escolhido = st.selectbox("Escolha um lançamento para Alterar ou Apagar:", ["-- Selecione um gasto --"] + opcoes_selecao)
        
        if item_escolhido != "-- Selecione um gasto --":
            numero_linha_sheets = int(item_escolhido.split(":")[0].replace("Linha ", ""))
            dados_da_linha = df.iloc[numero_linha_sheets - 2]
            
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                st.markdown("**✏️ Atualizar Dados**")
                with st.form(key=f"form_edicao_real_{numero_linha_sheets}"):
                    novo_valor_numerico = st.number_input(
                        "Novo Valor (R$)", 
                        value=float(dados_da_linha["Valor"]), 
                        step=0.01, 
                        format="%.2f"
                    )
                    novo_pago_por = st.selectbox(
                        "Alterar Quem Pagou", 
                        ["Rodrigo", "Aline"], 
                        index=["Rodrigo", "Aline"].index(dados_da_linha["Quem Pagou"])
                    )
                    
                    botao_gravar_alteracao = st.form_submit_button("💾 Confirmar e Gravar Alteração", use_container_width=True)
                    
                    if botao_gravar_alteracao:
                        try:
                            celula_d = f"D{numero_linha_sheets}"
                            celula_e = f"E{numero_linha_sheets}"
                            
                            aba.update_acell(celula_d, novo_valor_numerico)
                            aba.update_acell(celula_e, novo_pago_por)
                            
                            st.success("Alteração salva com sucesso!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao salvar: {e}")
                            
            with col_btn2:
                st.markdown("**🗑️ Excluir Definitivamente**")
                st.write("Deseja remover este registro da planilha?")
                botao_deletar_registro = st.button("🔴 APAGAR LANÇAMENTO", use_container_width=True)
                if botao_deletar_registro:
                    try:
                        aba.delete_rows(numero_linha_sheets)
                        st.success("Registro removido do Google Sheets!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao deletar: {e}")

        st.markdown("---")
        st.subheader("📋 Todos os Lançamentos do Mês")
        
        df_visualizacao = df.copy()
        df_visualizacao["Valor"] = df_visualizacao["Valor"].map(lambda x: f"R$ {x:,.2f}")
        st.dataframe(df_visualizacao, use_container_width=True)
        
    else:
        st.info("Nenhum gasto localizado na planilha para este mês.")
