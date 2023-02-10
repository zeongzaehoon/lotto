import pandas as pd
from pandas import json_normalize
import numpy as np

from urllib.request import urlopen
import json
import time

import os.path

# 1회차부터 수집해 returnValue가 False일 때까지 수집해 DF으로 만들고 CSV로 저장
class Lotto():
    def __init__(self, today):
        self.today = today


    def get_data():
        csv_path = "data/data.csv"
        cnt = 1
        returnValue = "success"
        while returnValue == "success":
            print(cnt)
            print(returnValue)
            if cnt == 1:
                response = urlopen(f"https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={cnt}")
                decode = response.read().decode("utf-8")
                data_json = json.loads(decode)
                datas = json_normalize(data_json)
            elif cnt != 1:
                response = urlopen(f"https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={cnt}")
                decode = response.read().decode("utf-8")
                data_json = json.loads(decode)
                data = json_normalize(data_json)
                datas = datas.append(data)
            cnt += 1
            returnValue = data_json['returnValue']
        
        print("get_data ::: END get data from API")
        datas.to_csv(csv_path)


    # 매주 월요일, 전 주 결과를 추가해 분석하고 당첨번호를 예측해야함
    def add_data():
        # 지정된 경로에 csv파일이 있다면?
        csv_path = "data/data.csv"
        if os.path.isfile(csv_path) == True:
                df = pd.read_csv(csv_path)
                last_drwNo = df.drwNo.iloc[-1] 
                while data_json.returnValue == 'success':
                    response = urlopen(f"https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={last_drwNo}")
                    decode = response.read().decode("utf-8")
                    data_json = json.loads(decode)
                    data = json_normalize(data_json)
                    df.append(data)
                    last_drwNo += 1
        df.to_csv(csv_path)


    # API로 수집한 데이터에서 필요한 데이터만 추출 / 형태, 데이터타입 변경
    def trans_dataframe(self):
        # 마지막 줄 제거
        self.df = self.df[0:-1]
        # 불필요한 칼럼 제거
        self.df = self.df[['drwNoDate', 'drwtNo1', 'drwtNo2', 'drwtNo3', 'drwtNo4', 'drwtNo5', 'drwtNo6', 'bnusNo']]
        # 인덱스 재설정
        self.df.reset_index(drop=True, inplace=True)
        # float -> int로 변경
        for c in self.df.columns:
            try:
                if self.df[c].dtype == 'float64':
                    self.df = self.df.astype({c:'int'})
            except:
                pass
        # 시계열
        self.df['drwNoDate'] = pd.to_datetime(self.df['drwNoDate'])


    def variable():
        pass


    def freq(self):
        modes = {}
        one_six = self.df.iloc[:, 1:-1]
        bonus = self.df.iloc[:, -1]
        
        for m in one_six:
            mode = one_six[m].mode().values[0]
            modes[m] = mode

        mode = bonus.mode().values[0]
        modes[bonus.name] = mode

        print(f"1회부터 지금까지 가장 많이 나온 번호 : {modes}")


    def freq_season(self):
        df_season = self.df[:]
        spring = [3, 4, 5]
        summer = [6, 7, 8]
        fall = [9, 10, 11]
        winter = [12, 1, 2]

        df_spring = pd.DataFrame()
        df_summer = pd.DataFrame()
        df_fall = pd.DataFrame()
        df_winter = pd.DataFrame()

        for i in df_season.index:
            if df_season['drwNoDate'][i].month in winter:
                # df_season.loc[i, 'season'] = "Winter"
                df_winter = pd.concat((df_winter, df_season.iloc[i:i+1]))
            elif df_season['drwNoDate'][i].month in spring:
                # df_season.loc[i, 'season'] = "Spring"
                df_spring = pd.concat((df_spring, df_season.iloc[i:i+1]))
            elif df_season['drwNoDate'][i].month in summer:
                # df_season.loc[i, 'season'] = "Summer"
                df_summer = pd.concat((df_summer, df_season.iloc[i:i+1]))
            elif df_season['drwNoDate'][i].month in fall:
                # df_season.loc[i, 'season'] = "Fall"
                df_fall = pd.concat((df_fall, df_season.iloc[i:i+1]))

        df_list = [df_spring, df_summer, df_fall, df_winter]

        season_list = ["spring", "summer", "fall", "winter"]
        modes_season = {}
        for s, d in zip(season_list, df_list):
            d.reset_index(drop=True, inplace=True)
            one_six = d.iloc[:, 1:-1]
            bonus = d.iloc[:, -1]
            modes = {}
            for i, m in enumerate(one_six):
                mode = one_six[m].mode().values[0]
                modes[m] = mode

            mode = bonus.mode().values[0]
            modes[bonus.name] = mode

            modes_season[s] = modes
            print("==========================계절별 가장 많이 나온 당첨번호 6개=======================")
            print(f"{s} : {modes}")


    def freq_month(self):
        df_concat = pd.DataFrame()
        df_month = self.df[:]
        modes_month = {}

        for m in range(1, 13, 1):
            for i in df_month.index:
                if df_month['drwNoDate'][i].month == m:
                    df_concat = pd.concat((df_concat, df_month.iloc[i:i+1]))

            df_concat.reset_index(drop=True, inplace=True)
            one_six = df_concat.iloc[:, 1:-1]
            bonus = df_concat.iloc[:, -1]
            modes = {}
            for md in one_six:
                mode = one_six[md].mode().values[0]
                modes[md] = mode

            mode = bonus.mode().values[0]
            modes[bonus.name] = mode

            modes_month[m] = modes
            print("==========================월별 가장 많이 나온 당첨번호 6개=======================")
            print(f"{m} : {modes}")


    def freq_year(self):
        # make year list
        year_list = np.unique([df['drwNoDate'][i].year for i in df['drwNoDate'].index])
        df_concat = pd.DataFrame()
        df_year = self.df[:]
        modes_year = {}

        for y in year_list:
            for i in df['drwNoDate'].index:
                if df_year['drwNoDate'][i].year == y:
                    df_concat = pd.concat((df_concat, df_year.iloc[i:i+1]))


            df_concat.reset_index(drop=True, inplace=True)
            one_six = df_concat.iloc[:, 1:-1]
            bonus = df_concat.iloc[:, -1]
            modes = {}
            for md in one_six:
                mode = one_six[md].mode().values[0]
                modes[md] = mode

            mode = bonus.mode().values[0]
            modes[bonus.name] = mode

            modes_year[y] = modes
            print("==========================연도별 가장 많이 나온 당첨번호 6개=======================")
            print(f"{y} : {modes}")
    

    def freq_choice(self):
        print("freq_choice ::: 1부터 45 중 번호 하나를 입력해주세요!")
        choice = int(input())
        df_concat = pd.DataFrame()
        modes_choice = {}
        df_choice = self.df[:]

        for i in df_choice.index:
            if choice in df_choice.iloc[i, 1:].values:
                df_concat = pd.concat((df_concat, df_choice.iloc[i:i+1]))
            else:
                pass

        df_concat.reset_index(drop=True, inplace=True)
        one_six = df_concat.iloc[:, 1:-1]
        modes = {}
        for md in one_six:
            mode = one_six[md].mode().values[0]
            modes[md] = mode

        modes_choice["choice"] = modes

        print(f" ")
        print(f"=========================={choice} 포함 가장 많이 나온 당첨번호 6개=======================")
        print(f"choice : {modes}")
        print(f" ")
        print(f"            ==========================DataFrame=======================")
        print(f"            ==========================================================")
        print(f" ")
        print(df_concat[-20:])
    

    def no_exist(self):
        number = [i for i in range(1, 46, 1)]

        for w in range(5, 16, 5):
            df_split = self.df.iloc[-w:, 1:]
            value_unique =  np.unique([df_split.iloc[i].values for i in range(len(df_split))])

            no_list = []
            for n in number:
                if n in value_unique: 
                    pass
                else:
                    no_list.append(n)
            
            print(f"{w}주간 나오지 않은 번호 : {no_list}")