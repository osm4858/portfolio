# 프로젝트 개요
상하이 증권거래소(SSE)의 15개년 일별 데이터 및 타임별 마켓 데이터를 효율적으로 처리하기 위해 2개의 데이터베이스 인프라(NoSQL vs 시계열 DB)를 설계하고 이를 활용한 퀀트 분석 시스템을 구축한 프로젝트

프로젝트 주요 언어: Python(ver.3.13.1)

# Task 1 
[pairs_trading_task1.py](Task%201/pairs_trading_task1.py)  파일 참조

__목표__: 2010년 이후 상하이 증권거래소(SSE)에서 거래된 모든 종목의 일일 과거 데이터 전체를 수집하고 저장하는 시스템을 개발

- def init: MongoDB URL 연결
- def get_sse_ticker: 상하이 증권거래소 주식들 리스트 설정
- def fetch_stock_data: 주식 데이터 수집
- def store_stock_data, def batch_fetch_and_store: 해당 데이터 및 다른 주식 데이터를 수집 후 MongoDB에 저장
- def update_daily_data, def get_stock_data(self, ticker, ...): 매일 데이터 업데이트 및 정보 가져오기

Flask를 이용하여 Rest API 연결
'GET' 사용
- def get_stock_data (): 변수 이름값을 생성하여 REST API 엔드포인트 만들기 (ticker, start_date, end_date, fields_param)
- 그후 json 파일로 변경

'POST' 사용
- def update_data(): json 파일로 업데이트 및 엔드포인드 만들기

Flask API server 실행

# Task 2
[pairs_trading_task2.py](Task%201/pairs_trading_task2.py)  파일 참조

__목표__: 다음과 같은 방법으로 데이터를 분석하여 중국 시장에서 통계적 차익거래 가능성을 탐색
<br />
1. 주식 간 상관관계 지표/모델 구축 <br />
2. 상관관계에 따라 주식을 그룹화하는 클러스터링 모델 구축 <br />
3. 클러스터와 상관관계를 기반으로 평균회귀 전략 수립 <br />
4. 전략 백테스팅 <br />

- def init: MongoDB 연결 및 분석할 내용 세팅
- def load_data: 분석하기 충분한 데이터 로딩
- def build_correlation_matrix(self): 주식들간의 상관 행렬 (correlation matrix) 생성 및 통계 데이터 표시
- def plot_correlation_heatmap: 히트맵 생성
- def cluster_stocks: K-평균 군집화 (K-means clustering) 생성
- def find_cointegrated_pairs: 가장 일정한 균형 관계 (cointegrated pairs)를 이루는 주식 2개 (쌍) 찾기
- def design_mean_reversion_strategy: 주식에서 평균 회귀 전략을 위해 균형 관계를 이루는 2개의 주식 선택
- def backtest_strategy: 백테스팅 하여 과거에 진행했을 경우 어떤 성과를 나타냈는지 표시
- def run_complete_analysis: 조건에 맞춰 분석 실행

# 결과

파일 실행 시 화면: [Processing.png](Task%201/Processing.png)
<br />
시각화 도표: [Figure_1.png](Task%201/Figure_1.png>)

# Task 3.1
[Task 3.1.py](Task%203/Task%203.1.py)  파일 참조

__목표__: 제공된 데이터를 호스팅하기 위해 시계열 데이터용이 아닌 NoSQL 데이터베이스 (CSV, JSON) 추출

- def init: MongoDB 연결
- def check_mongodb_running: MongoDB 연결 확인
- def create_database_structure: JSON 파일 형식의 데이터베이스 생성
- def load_csv_to_mongodb: 지정된 csv파일을 MongoDB로 불러오기
- def create_ticker_metadata: 주식 코드를 위한 메타데이터 생성
- def load_multiple_csvs: 여러개의 csv파일 불러오기
- def verify_data: 불러온 데이터 검사
- def run_complete_setup: 모든 세팅 확인 표시
- def main: CSV 파일 위치 물어보기

# Task 3.2







