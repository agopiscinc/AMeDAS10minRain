import streamlit as st
import time
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# CSVファイルの読み込み
kisho_df = pd.read_csv('kisyotyo_prec_block.csv', dtype='object')

# Streamlitアプリのタイトル
st.title("10分間隔気象データ取得アプリ")

# ユーザー入力

# デフォルト値の設定
default_prec = "東京都"

# 都道府県のセレクトボックスを表示
selected_prefecture = st.selectbox("都府県・地方を選択してください", kisho_df["prec_name"].unique(), index=kisho_df["prec_name"].unique().tolist().index(default_prec))

# 選択された都道府県に基づいて都市名のセレクトボックスを表示
selected_block = st.selectbox("観測所を選択してください", kisho_df[kisho_df["prec_name"] == selected_prefecture]["block_name"], index=min(4, len(kisho_df[kisho_df["prec_name"]==selected_prefecture])-1))

# place = st.text_input("観測地点名", "東京")
start_date = st.date_input("開始日", pd.to_datetime('2024-08-01'))
end_date = st.date_input("終了日", pd.to_datetime('2024-08-02'))
calculate_soil_water_index = st.checkbox("土壌雨量指数の計算", value=True)



def SWI_make(rains, raindata_dt=10):
    
    SWI = np.zeros(len(rains))
    
    #!parameter
    swi_L1 = 15
    swi_L2 = 60
    swi_L3 = 15
    swi_L4 = 15
    swi_a1 = 0.1
    swi_a2 = 0.15
    swi_a3 = 0.05
    swi_a4 = 0.01
    swi_b1 = 0.12
    swi_b2 = 0.05
    swi_b3 = 0.01
    swi_dt = raindata_dt/60

    #!initial
    swi_S1 = np.zeros(len(rains))
    swi_S2 = np.zeros(len(rains))
    swi_S3 = np.zeros(len(rains))
    swi_q1 = 0.0
    swi_q2 = 0.0
    swi_q3 = 0.0
    
    ###
    for i, rain in enumerate(rains):
        if i == 0:
            continue

        if(swi_S3[i-1] > swi_L4):
            swi_q3 = swi_a4*(swi_S3[i-1]-swi_L4)
            swi_S3[i] = (1-swi_b3*swi_dt)*swi_S3[i-1] - swi_q3*swi_dt + swi_b2*swi_S2[i-1]*swi_dt
            if(swi_S3[i]<0) :
                swi_S3[i] = 0.0
        else:
            swi_q3 = 0.0
            swi_S3[i] = (1-swi_b3*swi_dt)*swi_S3[i-1] - swi_q3*swi_dt + swi_b2*swi_S2[i-1]*swi_dt
            if(swi_S3[i]<0):
                swi_S3[i]=0.0

        if(swi_S2[i-1]>swi_L3):
            swi_q2 = swi_a3*(swi_S2[i-1]-swi_L3)
            swi_S2[i] = (1-swi_b2*swi_dt)*swi_S2[i-1]-swi_q2*swi_dt+swi_b1*swi_S1[i-1]*swi_dt
            if swi_S2[i]<0 :
                swi_S2[i]=0.0
        else:
            swi_q2 = 0.0
            swi_S2[i] = (1-swi_b2*swi_dt)*swi_S2[i-1]-swi_q2*swi_dt+swi_b1*swi_S1[i-1]*swi_dt
            if swi_S2[i]<0:
                swi_S2[i]=0.0

        if(swi_S1[i-1]>swi_L2):
            swi_q1 = swi_a1*(swi_S1[i-1]-swi_L1)+swi_a2*(swi_S1[i-1]-swi_L2)
            swi_S1[i] = (1-swi_b1*swi_dt)*swi_S1[i-1]-swi_q1*swi_dt+rains[i]#########
            if swi_S1[i]<0:
                swi_S1[i]=0.0
        elif swi_S1[i-1]>swi_L1:
            swi_q1 = swi_a1*(swi_S1[i-1]-swi_L1)
            swi_S1[i] = (1-swi_b1*swi_dt)*swi_S1[i-1]-swi_q1*swi_dt+rains[i]
            if swi_S1[i]<0:
                swi_S1[i]=0.0
        else:
            swi_q1 = 0.0
            swi_S1[i] = (1-swi_b1*swi_dt)*swi_S1[i-1]-swi_q1*swi_dt+rains[i]
            if swi_S1[i]<0:
                swi_S1[i]=0.0

        SWI[i] = swi_S1[i] + swi_S2[i] + swi_S3[i]
    return SWI




# ボタンをクリックするとデータを取得
if st.button("データ取得"):
    # 観測地点の情報取得
    kisho_df_ = kisho_df[kisho_df["prec_name"] == selected_prefecture]
    kisho_df_ = kisho_df_[kisho_df_["block_name"] == selected_block]
    prec_no = kisho_df_['prec_no'].values[0]
    block_no = kisho_df_['block_no'].values[0]
    ob_type = kisho_df_['ob_type'].values[0]
    
    # try:
    #     prec_no = no_df[no_df['place'] == place]['prec_no'].values[0]
    #     block_no = no_df[no_df['place'] == place]['block_no'].values[0]
    # except IndexError:
    #     st.error("観測地点名が見つかりません。正しい観測地点名を入力してください。")
    #     st.stop()

    # 期間レンジ
    date_range = pd.date_range(start_date, end_date, freq='D')


    

    df = pd.DataFrame()

    for date in date_range:
        st.write(f"データ取得中: {date}")
        
        if ob_type == 's':
            header = ['時分','気圧(hPa)_現地', '気圧(hPa)_海面', '降水量(mm)', '気温(℃)', '相対湿度(％)', '風向・風速_平均_風速(m/s)', '風向・風速_平均_風向', 
                      '風向・風速_最大瞬間_風速(m/s)', '風向・風速_最大瞬間_風向', '日照時間(min)']
        else:
            header = ['時分', '降水量(mm)', '気温(℃)', '相対湿度(％)', '風向・風速_平均_風速(m/s)', '風向・風速_平均_風向', 
                      '風向・風速_最大瞬間_風速(m/s)', '風向・風速_最大瞬間_風向', '日照時間(min)']

        url = f"https://www.data.jma.go.jp/obd/stats/etrn/view/10min_{ob_type}1.php?prec_no={prec_no}&block_no={block_no}&year={date.year}&month={date.month}&day={date.day}&view="

        
        # ウェブページの取得
        response = requests.get(url)
        response.encoding = response.apparent_encoding  # Handle Japanese characters
        
        # BeautifulSoupでHTMLをパース
        soup = BeautifulSoup(response.content, "html.parser")
        
        # テーブルデータの抽出
        table = soup.find('table', {'id': 'tablefix1'})
        
        if not table:
            st.error(f"{date} のデータが見つかりませんでした。")
            continue

        
        # テーブルの行を抽出
        rows = []
        for tr in table.find_all('tr')[3:]:
            cells = tr.find_all(['td', 'th'])
            row = [cell.text.strip() for cell in cells]
            rows.append(row)
        
        # DataFrameの作成
        df_ = pd.DataFrame(rows, columns=header)
        df_['日付'] = date

        df = pd.concat([df, df_])

    # 降雨データは日付境界を前の日の24:00:00と表記しているため修正
    idx = df[df['時分']=='24:00'].index
    df.loc[idx, '時分'] = '0:00'
    # datetime型の文字列を作成し，datetime型に
    df['datetime'] = df['日付'].astype(str)+ ' ' + df['時分']
    df['datetime'] = pd.to_datetime(df['datetime'])
    # idxに保存しておいた日付境界の日付を1日分進める
    df.loc[idx, 'datetime'] = df.loc[idx, 'datetime'] + pd.to_timedelta(1, unit='D')
    df.set_index('datetime', inplace=True)
    df.drop(columns=['時分', '日付'], inplace=True)

    if calculate_soil_water_index:
        # 土壌雨量指数の計算
        df['降水量(mm)'] = pd.to_numeric(df['降水量(mm)'], errors='coerce').fillna(0)
        raindata_dt = 10 #[min]
        df['土壌雨量指数'] = SWI_make(df['降水量(mm)'].to_numpy(), raindata_dt)
    
    # 結果の表示
    st.write("取得したデータ:")
    st.dataframe(df)
    # 必要に応じてCSVとしてダウンロードするオプションを追加
    csv = df.to_csv()
    st.download_button(label="CSVをダウンロード", data=csv, file_name=f'weather_data_{selected_block}_{start_date}_{end_date}.csv', mime='text/csv')




    # 結果の描画
    # 10 min Precipitation and Cumulative Rainfall
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig.add_trace(go.Bar(x=df.index, y=df['降水量(mm)'], name='Precipitation',), secondary_y=False)    
    fig.add_trace(go.Scatter(x=df.index, y=df['降水量(mm)'].cumsum(), name='Cumulative Rainfall', mode='lines', line=dict(color='red')), secondary_y=True)
    
    fig.update_layout(
        title='10 min Precipitation and Cumulative Rainfall',
        xaxis_title='Date',
        yaxis_title='Precipitation [mm/10min]',
        yaxis2=dict(
            title='Cumulative Rainfall [mm]',
            overlaying='y',
            side='right',
            range=[0, df['降水量(mm)'].cumsum().max()*1.05], 
            showgrid=False
        ),
        legend=dict(x=0.01, y=1.0)
    )

    st.plotly_chart(fig)


    # 1 hour Precipitation and SWI
    if calculate_soil_water_index:
        df_plt = df.select_dtypes('number').resample('h').sum()
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=df_plt.index, y=df_plt['降水量(mm)'], name='Precipitation',), secondary_y=False)
        fig.add_trace(go.Scatter(x=df.index, y=df['土壌雨量指数'], name='Soil Water Index',), secondary_y=True)
        
        fig.update_layout(
            title='1 hour Precipitation and Soil Water Index',
            xaxis_title='Date',
            yaxis_title='Precipitation [mm/hour]',
            yaxis2=dict(
                title='Soil Water Index',
                overlaying='y',
                side='right',
                range=[0, df['土壌雨量指数'].max()*1.05], 
                showgrid=False
            ),
            legend=dict(x=0.01, y=1.0)
        )
        st.plotly_chart(fig)


    # snake line
        df_plt = df.copy()
        df_plt['60分間積算雨量'] = df_plt['降水量(mm)'].rolling(6).sum()
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(x=df_plt['土壌雨量指数'], y=df_plt['60分間積算雨量'], name='Soil Water Index', mode = 'lines+markers',
                                hovertemplate='土壌雨量指数: %{x}<br>60分間積算雨量: %{y} mm<br>%{customdata}<extra></extra>', customdata=df_plt.index))
        
        fig.update_layout(
            title='Snake lines',
            xaxis=dict(
                title='土壌雨量指数',
                range=[0,max(400,df_plt['土壌雨量指数'].max()*1.05)],       
            ),
            yaxis=dict(
                title='60分間積算雨量 [mm/60min]',
                range=[0,max(100,df_plt['60分間積算雨量'].max()*1.05)]
            ),
            legend=dict(x=0.01, y=1.0)
        )
        fig.update_layout(margin=dict(l=1, r=1, b=1, t=30), height = 600)
        st.plotly_chart(fig, use_container_width=True)

        

