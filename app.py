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
aba_lancamento, aba_gerenciamento = st.tabs(["📝 Novo Lançamento", "⚙️ Histórico & Gerenciamento"])

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
            valor = st.number_input("Valor (R$)", min_value=0.0, step=10.0, format="%.2f", key="novo_valor")
        
        if tipo == "Fixa":
            descricao = st.selectbox("Selecione a Despesa Fixa", DESPESAS_FIXAS, key="nova_desc_fixa")
        else:
            descricao = st.text_input("Descrição da Despesa Eventual", key="nova_desc_eve")

        enviar = st.form_submit_button("Salvar Lançamento")

        if enviar and valor > 0:
            nova_linha = [data.strftime("%d/%m/%Y"), tipo, descricao, valor, pago_por]
            try:
                aba.append_row(nova_linha)
                st.success(f"Gasto de R$ {valor:.2f} gravado com sucesso!")
                st.rerun()
            except Exception as erro:
                st.error(f"Falha ao gravar os dados: {erro}")

# --- ABA 2: FECHAMENTO, EDIÇÃO E EXCLUSÃO ---
with aba_gerenciamento:
    st.header("🧮 Fechamento e Histórico")
    
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
        
        if total_rodrigo > total_aline:
            st.info(f"**Aline** deve fazer um Pix de **R$ {total_rodrigo - metade_ideal:,.2f}** para **Rodrigo**.")
        elif total_aline > total_rodrigo:
            st.info(f"**Rodrigo** deve fazer um Pix de **R$ {total_aline - metade_ideal:,.2f}** para **Aline**.")
        else:
            st.success("Contas equilibradas!")
            
        st.markdown("---")
        st.subheader("📋 Gerenciar Registros Lançados")
        
        opcoes_linhas = []
        for index, row in df.iterrows():
            opcoes_linhas.append(f"Linha {index + 2}: {row['Data']} - {row['Descrição']} (R$ {row['Valor']:.2f}) - Por {row['Quem Pagou']}")
            
        selecao = st.selectbox("Selecione um registro para Modificar ou Excluir:", ["Nenhum"] + opcoes_linhas)
        
        if selecao != "Nenhum":
            numero_linha_sheets = int(selecao.split(":")[0].replace("Linha ", ""))
            dados_linha_atual = df.iloc[numero_linha_sheets - 2]
            
            col_ed1, col_ed2 = st.columns(2)
            
            with col_ed1:
                st.write("🗑️ **Zona de Exclusão**")
                botao_deletar = st.button("🔴 APAGAR REGISTRO DEFINITIVAMENTE", use_container_width=True)
                if botao_deletar:
                    try:
                        aba.delete_rows(numero_linha_sheets)
                        st.success("Registro deletado com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao deletar: {e}")
                        
            with col_ed2:
                st.write("✏️ **Zona de Edição**")
                
                # CORREÇÃO CRÍTICA: Usando st.form para travar os dados editados e impedir que o refresh limpe o input antes do clique
                with st.form("form_edicao", clear_on_submit=False):
                    novo_val = st.number_input("Alterar Valor (R$)", value=float(dados_linha_atual["Valor"]), step=5.0)
                    novo_pago = st.selectbox("Alterar Quem Pagou", ["Rodrigo", "Aline"], index=["Rodrigo", "Aline"].index(dados_linha_atual["Quem Pagou"]))
                    botao_atualizar = st.form_submit_button("🟢 Salvar Alterações", use_container_width=True)
                    
                    if botao_atualizar:
                        try:
                            # Envia as alterações diretamente em lote para evitar problemas de sincronia
                            celula_valor = f"D{numero_linha_sheets}"
                            celula_pago = f"E{numero_linha_sheets}"
                            
                            aba.update_acell(celula_valor, novo_val)
                            aba.update_acell(celula_pago, novo_pago)
                            
                            st.success("Registro atualizado com sucesso no Google Sheets!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao atualizar: {e}")

        st.markdown("---")
        st.write("**Visualização Completa da Tabela:**")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Nenhum gasto localizado na planilha para este mês.")
