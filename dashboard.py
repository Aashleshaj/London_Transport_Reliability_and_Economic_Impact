from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / 'data'

transport_path = DATA_DIR / 'Status.csv'
merged_path = DATA_DIR / 'merged_transport_economic.csv'
summary_path = DATA_DIR / 'borough_disruption_summary.csv'

st.set_page_config(page_title='London Transport Dashboard', layout='wide')
st.title('London Transport Reliability & Economic Impact')

transport_df = pd.read_csv(transport_path)
merged_df = pd.read_csv(merged_path)
borough_summary = pd.read_csv(summary_path)

st.sidebar.header('Filters')
selected_boroughs = st.sidebar.multiselect(
    'Select borough(s)',
    sorted(borough_summary['borough'].dropna().unique()),
    default=sorted(borough_summary['borough'].dropna().unique())
)

filtered_merged = merged_df[merged_df['borough'].isin(selected_boroughs)]
filtered_summary = borough_summary[borough_summary['borough'].isin(selected_boroughs)]

st.header('Current Transport Status')
col1, col2 = st.columns(2)
with col1:
    st.metric('Lines reported', len(filtered_merged))
    st.metric('Boroughs selected', filtered_summary['borough'].nunique())
with col2:
    average_severity = filtered_summary['average_severity'].mean()
    st.metric('Average severity', f'{average_severity:.2f}')

st.subheader('Summary by Borough')
st.dataframe(filtered_summary)

st.subheader('Line-level Status')
st.dataframe(filtered_merged[['name', 'modeName', 'statusSeverity', 'statusSeverityDescription', 'borough']])

st.subheader('Severity by Borough')
fig = px.bar(
    filtered_summary,
    x='borough',
    y='average_severity',
    labels={'average_severity': 'Average Severity'},
    title='Average Disruption Severity by Borough'
)
st.plotly_chart(fig, use_container_width=True)

st.subheader('Economic Context')
fig2 = px.scatter(
    filtered_summary,
    x='total_gva_m',
    y='average_severity',
    text='borough',
    labels={'total_gva_m': 'Borough GVA (£m)', 'average_severity': 'Average Severity'},
    title='GVA vs Disruption Severity'
)
fig2.update_traces(textposition='top center')
st.plotly_chart(fig2, use_container_width=True)

st.subheader('Employment Context')
fig3 = px.scatter(
    filtered_summary,
    x='total_employees',
    y='average_severity',
    text='borough',
    labels={'total_employees': 'Total Employees', 'average_severity': 'Average Severity'},
    title='Employment vs Disruption Severity'
)
fig3.update_traces(textposition='top center')
st.plotly_chart(fig3, use_container_width=True)

st.write('Use the sidebar to select boroughs and explore how transport reliability relates to borough-level economic metrics. Replace `data/economic_data.csv` with real ONS/GLA borough data if needed.')