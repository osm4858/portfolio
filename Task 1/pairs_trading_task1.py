# Task 1: Data Management System for Shanghai Stock Exchange
# This script handles data fetching, MongoDB storage, and REST API

import yfinance as yf
import pandas as pd
from pymongo import MongoClient
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import requests
from concurrent.futures import ThreadPoolExecutor
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SSEDataManager:
    def __init__(self, mongodb_uri="mongodb://localhost:27017/", db_name="sse_trading"):
        """
        Initialize the data manager
        
        Args:
            mongodb_uri: MongoDB connection string
            db_name: Database name
        """
        self.client = MongoClient(mongodb_uri)
        self.db = self.client[db_name]
        self.collection = self.db.stock_data
        
        # Create indexes for better query performance
        self.collection.create_index([("ticker", 1), ("date", 1)])
        
    def get_sse_tickers(self):
        """
        Get list of Shanghai Stock Exchange tickers
        Note: This is a simplified list. In practice, you'd fetch from official sources
        """
        # Shanghai A-share stocks typically end with .SS
        # Sample list - you should expand this with actual SSE stocks
        sample_tickers = [
            "600000.SS", "600036.SS", "600519.SS", "000001.SS", "000002.SS",
            "600887.SS", "601318.SS", "600276.SS", "600028.SS", "601166.SS",
            "600030.SS", "601328.SS", "601288.SS", "600585.SS", "600900.SS",
            "601012.SS", "600104.SS", "600309.SS", "600837.SS", "600048.SS"
        ]
        return sample_tickers
    
    def fetch_stock_data(self, ticker, start_date="2010-01-01", end_date=None):
        """
        Fetch historical data for a single stock
        
        Args:
            ticker: Stock ticker symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD), defaults to today
        """
        try:
            if end_date is None:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            logger.info(f"Fetching data for {ticker}")
            stock = yf.Ticker(ticker)
            data = stock.history(start=start_date, end=end_date)
            
            if data.empty:
                logger.warning(f"No data found for {ticker}")
                return None
            
            # Prepare data for MongoDB
            records = []
            for date, row in data.iterrows():
                record = {
                    'ticker': ticker,
                    'date': date.strftime('%Y-%m-%d'),
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                    'volume': int(row['Volume']),
                    'dividends': float(row['Dividends']),
                    'stock_splits': float(row['Stock Splits'])
                }
                records.append(record)
            
            return records
        
        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {e}")
            return None
    
    def store_stock_data(self, ticker, start_date="2010-01-01", end_date=None):
        """
        Store stock data in MongoDB
        """
        records = self.fetch_stock_data(ticker, start_date, end_date)
        
        if records:
            try:
                # Use upsert to avoid duplicates
                for record in records:
                    self.collection.update_one(
                        {'ticker': record['ticker'], 'date': record['date']},
                        {'$set': record},
                        upsert=True
                    )
                logger.info(f"Stored {len(records)} records for {ticker}")
                return True
            except Exception as e:
                logger.error(f"Error storing data for {ticker}: {e}")
                return False
        return False
    
    def batch_fetch_and_store(self, max_workers=5):
        """
        Fetch and store data for all SSE stocks using threading
        """
        tickers = self.get_sse_tickers()
        logger.info(f"Starting batch fetch for {len(tickers)} tickers")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self.store_stock_data, ticker) for ticker in tickers]
            
            for i, future in enumerate(futures):
                try:
                    result = future.result()
                    if result:
                        logger.info(f"Completed {i+1}/{len(tickers)} tickers")
                    time.sleep(0.5)  # Rate limiting
                except Exception as e:
                    logger.error(f"Error in batch processing: {e}")
    
    def update_daily_data(self):
        """
        Update database with latest daily data
        """
        logger.info("Starting daily data update")
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        today = datetime.now().strftime('%Y-%m-%d')
        
        tickers = self.get_sse_tickers()
        
        for ticker in tickers:
            self.store_stock_data(ticker, start_date=yesterday, end_date=today)
            time.sleep(0.2)  # Rate limiting
        
        logger.info("Daily data update completed")
    
    def get_stock_data(self, ticker, start_date, end_date, fields=None):
        """
        Retrieve stock data from MongoDB
        
        Args:
            ticker: Stock ticker
            start_date: Start date
            end_date: End date
            fields: List of fields to return
        """
        query = {
            'ticker': ticker,
            'date': {'$gte': start_date, '$lte': end_date}
        }
        
        projection = {'_id': 0}
        if fields:
            for field in fields:
                projection[field] = 1
            projection['date'] = 1  # Always include date
        
        cursor = self.collection.find(query, projection).sort('date', 1)
        return list(cursor)

# Flask REST API
app = Flask(__name__)
data_manager = SSEDataManager()

@app.route('/api/stock-data', methods=['GET'])
def get_stock_data():
    """
    REST API endpoint to get stock data
    
    Parameters:
    - ticker: Stock ticker (required)
    - start_date: Start date in YYYY-MM-DD format (required)
    - end_date: End date in YYYY-MM-DD format (required)
    - fields: Comma-separated list of fields (optional)
    """
    try:
        ticker = request.args.get('ticker')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        fields_param = request.args.get('fields')
        
        if not all([ticker, start_date, end_date]):
            return jsonify({'error': 'Missing required parameters'}), 400
        
        fields = fields_param.split(',') if fields_param else None
        
        data = data_manager.get_stock_data(ticker, start_date, end_date, fields)
        
        return jsonify({
            'ticker': ticker,
            'start_date': start_date,
            'end_date': end_date,
            'data': data
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/update-data', methods=['POST'])
def update_data():
    """
    Endpoint to trigger data update
    """
    try:
        data_manager.update_daily_data()
        return jsonify({'message': 'Data update completed'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    # Initialize data if needed
    print("Starting SSE Data Management System")
    print("1. Make sure MongoDB is running")
    print("2. Install required packages: pip install yfinance pymongo flask pandas")
    print("3. To fetch initial data, uncomment the line below:")
    
    # Uncomment this line to fetch initial data (run once)
    data_manager.batch_fetch_and_store()
    
    # Start Flask API server
    app.run(debug=False, host='0.0.0.0', port=5000)
