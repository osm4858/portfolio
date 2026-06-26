# 프로젝트 개요
상하이 증권거래소(SSE)의 15개년 일별 데이터 및 타임별 마켓 데이터를 효율적으로 처리하기 위해 2개의 데이터베이스 인프라(NoSQL vs 시계열 DB)를 설계하고 이를 활용한 퀀트 분석 시스템을 구축한 프로젝트

프로젝트 주요 언어: Python(ver.3.13.7)

# Task 1 
[pairs_trading_task.py](Task%201/pairs_trading_task1.py) 파일 참조

- def __init__: MongoDB URL 연결
- def get_sse_ticker: 상하이 증권거래소 주식들 리스트 설정
- def fetch_stock_data: 주식 데이터 수집
- def store_stock_data, def batch_fetch_and_store: 해당 데이터 및 다른 주식 데이터를 수집 후 MongoDB에 저장
- def update_daily_data, def get_stock_data(self, ticker, ...): 매일 데이터 업데이트 및 정보 가져오기

Flask를 이용하여 Rest API 연결
'GET' 사용
- def get_stock_data (): 변수 이름값을 생성하여 REST API 엔드포인트 만들기 (ticker, start_date, end_date, fields_param)
- 그후 json 파일로 변경

'POST' 사용
- def update_data(): json 파일로 업데이트랑 엔드포인드 만들기

Flask API server 실행

# Task 2
