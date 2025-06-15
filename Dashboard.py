import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(
    page_title="Smart Manufacturing Analytics",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stMetric {
        border-left: 5px solid #4CAF50;
        padding-left: 15px;
    }
    .stAlert {
        border-radius: 10px;
    }
    .st-b7 {
        color: #ffffff;
    }
    .reportview-container .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    dados = pd.read_csv('smart_manufacturing_data_processed.csv')
    dados['timestamp'] = pd.to_datetime(dados['timestamp'])
    dados['date'] = dados['timestamp'].dt.date
    dados['time'] = dados['timestamp'].dt.time
    dados['hour'] = dados['timestamp'].dt.hour
    dados['day_part'] = pd.cut(dados['hour'],
                             bins=[0, 6, 12, 18, 24],
                             labels=['Madrugada', 'Manhã', 'Tarde', 'Noite'],
                             right=False)
    return dados

dados = load_data()

st.sidebar.header("🔍 Filtros Avançados")

maquinas_disponiveis = dados['machine'].unique()
maquinas_selecionadas = st.sidebar.multiselect(
    "Selecione as máquinas:",
    options=maquinas_disponiveis,
    default=maquinas_disponiveis[:5]
)

min_date = dados['date'].min()
max_date = dados['date'].max()
date_range = st.sidebar.date_input(
    "Selecione o intervalo de datas:",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

status_options = dados['machine_status'].unique()
status_selecionados = st.sidebar.multiselect(
    "Status da máquina:",
    options=status_options,
    default=status_options
)

filtro_manutencao = st.sidebar.radio(
    "Manutenção necessária:",
    options=['Todas', 'Apenas com manutenção', 'Sem manutenção'],
    index=0
)

tipos_falha = dados['failure_type'].unique()
filtro_falha = st.sidebar.multiselect(
    "Tipo de falha:",
    options=tipos_falha,
    default=tipos_falha
)

dados_filtrados = dados[
    (dados['machine'].isin(maquinas_selecionadas)) &
    (dados['date'] >= date_range[0]) &
    (dados['date'] <= date_range[1]) &
    (dados['machine_status'].isin(status_selecionados)) &
    (dados['failure_type'].isin(filtro_falha))
]

if filtro_manutencao == 'Apenas com manutenção':
    dados_filtrados = dados_filtrados[dados_filtrados['maintenance_required'] == 'Yes']
elif filtro_manutencao == 'Sem manutenção':
    dados_filtrados = dados_filtrados[dados_filtrados['maintenance_required'] == 'No']

if len(dados_filtrados) == 0:
    st.warning("⚠️ Nenhum dado encontrado com os filtros atuais. Ajuste os critérios de filtragem.")
    st.stop()

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Visão Geral", 
    "🏭 Análise por Máquina", 
    "⚠️ Monitoramento de Falhas", 
    "📥 Download de Dados"
])

with tab1:
    st.header("Visão Geral das Máquinas")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total de Máquinas", len(maquinas_selecionadas))
    col2.metric("Registros Analisados", len(dados_filtrados))
    
    falhas = dados_filtrados[dados_filtrados['machine_status'] == 'Failure']
    col3.metric("Falhas Detectadas", len(falhas))
    
    taxa_falha = len(falhas) / len(dados_filtrados) * 100 if len(dados_filtrados) > 0 else 0
    col4.metric("Taxa de Falha", f"{taxa_falha:.2f}%")
    
    st.subheader("Distribuição de Status das Máquinas")
    status_counts = dados_filtrados['machine_status'].value_counts().reset_index()
    status_counts.columns = ['Status', 'Contagem']
    
    fig1 = px.pie(
        status_counts,
        values='Contagem',
        names='Status',
        color='Status',
        color_discrete_map={
            'Running': '#2ecc71',
            'Idle': '#f39c12',
            'Failure': '#e74c3c'
        },
        hole=0.3
    )
    st.plotly_chart(fig1, use_container_width=True)
    
    st.subheader("Média dos Sensores por Máquina")
    sensor_metrics = dados_filtrados.groupby('machine')[['temperature', 'vibration', 'humidity', 'pressure', 'energy_consumption']].mean().reset_index()
    
    sensor_selecionado = st.selectbox(
        "Selecione o sensor para análise:",
        ['temperature', 'vibration', 'humidity', 'pressure', 'energy_consumption'],
        key='sensor_maquina'
    )
    
    fig2 = px.bar(
        sensor_metrics.sort_values(sensor_selecionado, ascending=False),
        x='machine',
        y=sensor_selecionado,
        color='machine',
        title=f"Média de {sensor_selecionado.capitalize()} por Máquina",
        labels={'machine': 'Máquina', sensor_selecionado: sensor_selecionado.capitalize()}
    )
    st.plotly_chart(fig2, use_container_width=True)
    
    st.subheader("Correlação entre Sensores")
    variaveis_correlacao = st.multiselect(
        "Selecione sensores para análise de correlação:",
        ['temperature', 'vibration', 'humidity', 'pressure', 'energy_consumption'],
        default=['temperature', 'vibration', 'energy_consumption'],
        key='var_correlacao'
    )
    
    if len(variaveis_correlacao) >= 2:
        corr_matrix = dados_filtrados[variaveis_correlacao].corr()
        fig3 = px.imshow(
            corr_matrix,
            text_auto=True,
            color_continuous_scale='RdBu',
            title="Correlação entre Sensores",
            aspect="auto"
        )
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.warning("Selecione pelo menos 2 sensores para análise de correlação.")

with tab2:
    st.header("Análise Detalhada por Máquina")
    
    maquina_selecionada = st.selectbox(
        "Selecione uma máquina para análise detalhada:",
        maquinas_selecionadas,
        key='maquina_selecionada'
    )
    
    dados_maquina = dados_filtrados[dados_filtrados['machine'] == maquina_selecionada]
    
    st.subheader(f"Métricas da Máquina {maquina_selecionada}")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Último Status", dados_maquina['machine_status'].iloc[-1])
    col2.metric("Temperatura Atual", f"{dados_maquina['temperature'].iloc[-1]:.1f}°C")
    col3.metric("Vibração Atual", f"{dados_maquina['vibration'].iloc[-1]:.1f}")
    col4.metric("Vida Útil Restante", f"{dados_maquina['predicted_remaining_life'].iloc[-1]} horas")
    
    st.subheader(f"Série Temporal dos Sensores - Máquina {maquina_selecionada}")
    variaveis_ts = st.multiselect(
        "Selecione sensores para série temporal:",
        ['temperature', 'vibration', 'humidity', 'pressure', 'energy_consumption'],
        default=['temperature', 'vibration'],
        key='var_series_temporais'
    )
    
    if variaveis_ts:
        fig4 = go.Figure()
        cores = px.colors.qualitative.Plotly
        for i, var in enumerate(variaveis_ts):
            fig4.add_trace(go.Scatter(
                x=dados_maquina['timestamp'],
                y=dados_maquina[var],
                name=var.capitalize(),
                mode='lines',
                line=dict(color=cores[i], width=2),
                yaxis=f'y{i+1}' if i > 0 else 'y'
            ))
        
        if len(variaveis_ts) > 1:
            fig4.update_layout(
                yaxis=dict(title=variaveis_ts[0].capitalize()),
                yaxis2=dict(
                    title=variaveis_ts[1].capitalize(),
                    overlaying='y',
                    side='right'
                )
            )
        
        fig4.update_layout(
            title=f"Série Temporal para Máquina {maquina_selecionada}",
            xaxis_title='Tempo',
            hovermode='x unified'
        )
        st.plotly_chart(fig4, use_container_width=True)
    
    st.subheader("Padrões Diários")
    variavel_padrao = st.selectbox(
        "Selecione o sensor para análise de padrão diário:",
        ['temperature', 'vibration', 'energy_consumption'],
        key='var_padrao_diario'
    )
    
    dados_hora = dados_maquina.groupby('hour')[variavel_padrao].mean().reset_index()
    fig5 = px.line(
        dados_hora,
        x='hour',
        y=variavel_padrao,
        title=f"Padrão Diário de {variavel_padrao.capitalize()}",
        labels={'hour': 'Hora do Dia', variavel_padrao: variavel_padrao.capitalize()}
    )
    st.plotly_chart(fig5, use_container_width=True)

with tab3:
    st.header("Monitoramento de Falhas")
    
    st.subheader("Detecção de Anomalias")
    col1, col2 = st.columns(2)
    temp_limite = col1.slider("Limite de Temperatura para Anomalia (°C):", 50, 120, 90)
    vib_limite = col2.slider("Limite de Vibração para Anomalia:", 0, 100, 70)
    
    anomalias = dados_filtrados[
        (dados_filtrados['temperature'] > temp_limite) | 
        (dados_filtrados['vibration'] > vib_limite)
    ]
    
    if not anomalias.empty:
        fig6 = px.scatter(
            anomalias,
            x='timestamp',
            y='temperature',
            color='vibration',
            size='energy_consumption',
            hover_data=['machine', 'failure_type'],
            title="Eventos Anômalos Detectados",
            color_continuous_scale='thermal'
        )
        st.plotly_chart(fig6, use_container_width=True)
        
        st.subheader("Resumo das Anomalias")
        st.dataframe(
            anomalias[['machine', 'timestamp', 'temperature', 'vibration', 'failure_type']].sort_values('timestamp', ascending=False),
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("Nenhuma anomalia detectada com os critérios atuais")
    
    st.subheader("Tipos de Falha Detectadas")
    falhas = dados_filtrados[dados_filtrados['failure_type'] != 'Normal']
    if not falhas.empty:
        tipos_falha = falhas['failure_type'].value_counts().reset_index()
        tipos_falha.columns = ['Tipo de Falha', 'Contagem']
        
        fig7 = px.bar(
            tipos_falha,
            x='Tipo de Falha',
            y='Contagem',
            color='Tipo de Falha',
            title="Distribuição dos Tipos de Falha"
        )
        st.plotly_chart(fig7, use_container_width=True)
    else:
        st.info("Nenhuma falha detectada no período selecionado.")
    
    st.subheader("Máquinas que Precisam de Manutenção")
    manutencao = dados_filtrados[dados_filtrados['maintenance_required'] == 'Yes']
    if not manutencao.empty:
        manutencao_agrupado = manutencao.groupby('machine').size().reset_index()
        manutencao_agrupado.columns = ['Máquina', 'Registros com necessidade']
        
        fig8 = px.bar(
            manutencao_agrupado.sort_values('Registros com necessidade', ascending=False),
            x='Máquina',
            y='Registros com necessidade',
            color='Máquina',
            title="Máquinas que Precisam de Manutenção"
        )
        st.plotly_chart(fig8, use_container_width=True)
    else:
        st.info("Nenhuma máquina com necessidade de manutenção no período selecionado.")

with tab4:
    st.header("Download de Dados")
    
    st.write("Visualize e faça download dos dados filtrados:")
    st.dataframe(dados_filtrados, height=300)
    
    st.subheader("Opções de Download")
    
    formato = st.radio(
        "Selecione o formato do arquivo:",
        ('CSV', 'JSON'),
        horizontal=True
    )
    
    nome_arquivo = st.text_input(
        "Nome do arquivo (sem extensão):",
        f"dados_manufatura_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    
    if st.button("Gerar Arquivo para Download"):
        if formato == 'CSV':
            csv = dados_filtrados.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="⬇️ Baixar CSV",
                data=csv,
                file_name=f"{nome_arquivo}.csv",
                mime='text/csv'
            )
        elif formato == 'JSON':
            json = dados_filtrados.to_json(orient='records', indent=2)
            st.download_button(
                label="⬇️ Baixar JSON",
                data=json,
                file_name=f"{nome_arquivo}.json",
                mime='application/json'
            )

st.markdown("---")
st.markdown("""
**Dashboard desenvolvido para Avaliação A1/2 - Digitalização**  
*Última atualização: {}*
""".format(datetime.now().strftime('%d/%m/%Y %H:%M')))