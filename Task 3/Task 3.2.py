"""
Task 1.03: REST API for Market Data
Complete Flask API to expose data from both QuestDB and MongoDB
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import pymongo
from pymongo import MongoClient
import pandas as pd
from datetime import datetime, timedelta
import json
import time
from typing import List, Dict, Any

app = Flask(__name__)
CORS(app)

class DatabaseConnections:
    """Manage database connections"""
    
    def __init__(self):
        # QuestDB connection
        self.questdb_conn = None
        self.mongodb_client = None
        self.mongodb_db = None
        self.connect_databases()
    
    def connect_databases(self):
        """Initialize database connections"""
        try:
            # Connect to QuestDB (PostgreSQL wire protocol)
            self.questdb_conn = psycopg2.connect(
                host='localhost',
                port=8812,
                user='admin',
                password='quest',
                database='qdb'
            )
            print("✅ Connected to QuestDB")
        except Exception as e:
            print(f"❌ QuestDB connection failed: {e}")
        
        try:
            # Connect to MongoDB
            self.mongodb_client = MongoClient("mongodb://localhost:27017/")
            self.mongodb_db = self.mongodb_client['market_data_db']
            print("✅ Connected to MongoDB")
        except Exception as e:
            print(f"❌ MongoDB connection failed: {e}")
    
    def get_questdb_connection(self):
        """Get QuestDB connection"""
        if self.questdb_conn and self.questdb_conn.closed == 0:
            return self.questdb_conn
        else:
            # Reconnect if connection is closed
            self.connect_databases()
            return self.questdb_conn
    
    def get_mongodb_collection(self):
        """Get MongoDB collection"""
        return self.mongodb_db['intraday_market_data']

# Global database connections
db_connections = DatabaseConnections()

class MarketDataAPI:
    """Market Data API handler"""
    
    @staticmethod
    def validate_request_params(start_time: str, end_time: str, tickers: List[str], fields: List[str]):
        """Validate API request parameters"""
        errors = []
        
        # Validate dates
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            
            if start_dt >= end_dt:
                errors.append("start_time must be before end_time")
        except ValueError as e:
            errors.append(f"Invalid date format: {e}")
        
        # Validate tickers
        if not tickers or not all(ticker.strip() for ticker in tickers):
            errors.append("At least one valid ticker is required")
        
        # Validate fields
        valid_fields = ['open', 'high', 'low', 'close', 'volume', 'vwap', 'trade_count']
        invalid_fields = [field for field in fields if field not in valid_fields]
        if invalid_fields:
            errors.append(f"Invalid fields: {invalid_fields}")
        
        return errors
    
    @staticmethod
    def query_questdb(start_time: str, end_time: str, tickers: List[str], fields: List[str]):
        """Query data from QuestDB"""
        start_query_time = time.time()
        
        try:
            conn = db_connections.get_questdb_connection()
            if not conn:
                raise Exception("QuestDB connection not available")
            
            cursor = conn.cursor()
            
            # Build SQL query - using 'date' column instead of 'timestamp'
            field_str = ', '.join(['date'] + fields)
            ticker_placeholders = ','.join(['%s'] * len(tickers))
            
            query = f"""
            SELECT {field_str}
            FROM intraday_market_data 
            WHERE date BETWEEN %s AND %s 
            ORDER BY date
            """
            
            params = [start_time, end_time]
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Get column names
            column_names = [desc[0] for desc in cursor.description]
            
            # Convert to list of dictionaries
            results = []
            for row in rows:
                row_dict = dict(zip(column_names, row))
                # Convert date to ISO string if it's a datetime object
                if 'date' in row_dict and row_dict['date']:
                    if hasattr(row_dict['date'], 'isoformat'):
                        row_dict['date'] = row_dict['date'].isoformat()
                results.append(row_dict)
            
            query_time = time.time() - start_query_time
            
            return {
                'success': True,
                'data': results,
                'count': len(results),
                'query_time_seconds': round(query_time, 4),
                'database': 'QuestDB'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'database': 'QuestDB'
            }
    
    @staticmethod
    def query_mongodb(start_time: str, end_time: str, tickers: List[str], fields: List[str]):
        """Query data from MongoDB"""
        start_query_time = time.time()
        
        try:
            collection = db_connections.get_mongodb_collection()
            if collection is None:
                raise Exception("MongoDB connection not available")
            
            # Convert dates for MongoDB
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            
            # Build MongoDB query
            match_stage = {
                'timestamp': {'$gte': start_dt, '$lte': end_dt},
                'ticker': {'$in': tickers}
            }
            
            # Build projection for requested fields
            projection = {'_id': 0, 'timestamp': 1, 'ticker': 1, 'date': 1}
            
            # Map API fields to MongoDB document structure
            field_mapping = {
                'open': 'ohlcv.open',
                'high': 'ohlcv.high', 
                'low': 'ohlcv.low',
                'close': 'ohlcv.close',
                'volume': 'ohlcv.volume',
                'vwap': 'market_data.vwap',
                'trade_count': 'market_data.trade_count'
            }
            
            for field in fields:
                if field in field_mapping:
                    projection[field_mapping[field]] = 1
            
            # Execute query
            cursor = collection.find(match_stage, projection).sort('timestamp', 1)
            
            # Process results
            results = []
            for doc in cursor:
                result_doc = {
                    'timestamp': doc['timestamp'].isoformat() if doc.get('timestamp') else None,
                    'ticker': doc.get('ticker'),
                    'date': doc.get('date')
                }
                
                # Extract requested fields
                for field in fields:
                    if field in ['open', 'high', 'low', 'close', 'volume']:
                        result_doc[field] = doc.get('ohlcv', {}).get(field)
                    elif field in ['vwap', 'trade_count']:
                        result_doc[field] = doc.get('market_data', {}).get(field)
                
                results.append(result_doc)
            
            query_time = time.time() - start_query_time
            
            return {
                'success': True,
                'data': results,
                'count': len(results),
                'query_time_seconds': round(query_time, 4),
                'database': 'MongoDB'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'database': 'MongoDB'
            }

# API Routes

@app.route('/api/market-data/questdb', methods=['GET'])
def get_market_data_questdb():
    """
    Get market data from QuestDB
    
    Query Parameters:
    - start_time: Start time in ISO format (e.g., 2024-01-01T00:00:00Z)
    - end_time: End time in ISO format (e.g., 2024-01-02T00:00:00Z)  
    - tickers: Comma-separated list of tickers (e.g., AAPL,GOOGL,MSFT)
    - fields: Comma-separated list of fields (e.g., open,high,low,close,volume)
    """
    try:
        # Parse query parameters
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        tickers_str = request.args.get('tickers', '')
        fields_str = request.args.get('fields', 'open,high,low,close,volume')
        
        # Convert to lists
        tickers = [t.strip().upper() for t in tickers_str.split(',') if t.strip()]
        fields = [f.strip().lower() for f in fields_str.split(',') if f.strip()]
        
        # Validate parameters
        validation_errors = MarketDataAPI.validate_request_params(start_time, end_time, tickers, fields)
        if validation_errors:
            return jsonify({
                'success': False,
                'errors': validation_errors
            }), 400
        
        # Query QuestDB
        result = MarketDataAPI.query_questdb(start_time, end_time, tickers, fields)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'database': 'QuestDB'
        }), 500

@app.route('/api/market-data/mongodb', methods=['GET'])
def get_market_data_mongodb():
    """
    Get market data from MongoDB
    
    Query Parameters:
    - start_time: Start time in ISO format (e.g., 2024-01-01T00:00:00Z)
    - end_time: End time in ISO format (e.g., 2024-01-02T00:00:00Z)
    - tickers: Comma-separated list of tickers (e.g., AAPL,GOOGL,MSFT)
    - fields: Comma-separated list of fields (e.g., open,high,low,close,volume)
    """
    try:
        # Parse query parameters
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        tickers_str = request.args.get('tickers', '')
        fields_str = request.args.get('fields', 'open,high,low,close,volume')
        
        # Convert to lists
        tickers = [t.strip().upper() for t in tickers_str.split(',') if t.strip()]
        fields = [f.strip().lower() for f in fields_str.split(',') if f.strip()]
        
        # Validate parameters
        validation_errors = MarketDataAPI.validate_request_params(start_time, end_time, tickers, fields)
        if validation_errors:
            return jsonify({
                'success': False,
                'errors': validation_errors
            }), 400
        
        # Query MongoDB
        result = MarketDataAPI.query_mongodb(start_time, end_time, tickers, fields)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'database': 'MongoDB'
        }), 500

@app.route('/api/market-data/compare', methods=['GET'])
def compare_databases():
    """
    Compare performance between QuestDB and MongoDB for the same query
    """
    try:
        # Parse query parameters
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        tickers_str = request.args.get('tickers', '')
        fields_str = request.args.get('fields', 'open,high,low,close,volume')
        
        # Convert to lists
        tickers = [t.strip().upper() for t in tickers_str.split(',') if t.strip()]
        fields = [f.strip().lower() for f in fields_str.split(',') if f.strip()]
        
        # Validate parameters
        validation_errors = MarketDataAPI.validate_request_params(start_time, end_time, tickers, fields)
        if validation_errors:
            return jsonify({
                'success': False,
                'errors': validation_errors
            }), 400
        
        # Query both databases
        questdb_result = MarketDataAPI.query_questdb(start_time, end_time, tickers, fields)
        mongodb_result = MarketDataAPI.query_mongodb(start_time, end_time, tickers, fields)
        
        # Compare results
        comparison = {
            'query_parameters': {
                'start_time': start_time,
                'end_time': end_time,
                'tickers': tickers,
                'fields': fields
            },
            'questdb': {
                'success': questdb_result['success'],
                'count': questdb_result.get('count', 0),
                'query_time_seconds': questdb_result.get('query_time_seconds', 0),
                'error': questdb_result.get('error')
            },
            'mongodb': {
                'success': mongodb_result['success'],
                'count': mongodb_result.get('count', 0),  
                'query_time_seconds': mongodb_result.get('query_time_seconds', 0),
                'error': mongodb_result.get('error')
            }
        }
        
        # Add performance comparison if both succeeded
        if questdb_result['success'] and mongodb_result['success']:
            questdb_time = questdb_result['query_time_seconds']
            mongodb_time = mongodb_result['query_time_seconds']
            
            if questdb_time > 0 and mongodb_time > 0:
                if questdb_time < mongodb_time:
                    faster_db = 'QuestDB'
                    speedup = round(mongodb_time / questdb_time, 2)
                else:
                    faster_db = 'MongoDB'
                    speedup = round(questdb_time / mongodb_time, 2)
                
                comparison['performance_analysis'] = {
                    'faster_database': faster_db,
                    'speedup_factor': f"{speedup}x",
                    'time_difference_seconds': round(abs(questdb_time - mongodb_time), 4)
                }
        
        return jsonify(comparison)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    questdb_status = "connected" if db_connections.questdb_conn and db_connections.questdb_conn.closed == 0 else "disconnected"
    mongodb_status = "connected" if db_connections.mongodb_client else "disconnected"
    
    return jsonify({
        'status': 'healthy',
        'databases': {
            'questdb': questdb_status,
            'mongodb': mongodb_status
        },
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/docs', methods=['GET'])
def api_documentation():
    """API documentation"""
    docs = {
        'title': 'Market Data API',
        'version': '1.0.0',
        'description': 'REST API for querying intraday market data from QuestDB and MongoDB',
        'endpoints': {
            'GET /api/market-data/questdb': {
                'description': 'Query market data from QuestDB',
                'parameters': {
                    'start_time': 'Start time in ISO format (required)',
                    'end_time': 'End time in ISO format (required)', 
                    'tickers': 'Comma-separated ticker symbols (required)',
                    'fields': 'Comma-separated field names (optional, default: open,high,low,close,volume)'
                },
                'example': '/api/market-data/questdb?start_time=2024-01-01T00:00:00Z&end_time=2024-01-02T00:00:00Z&tickers=ADANIENT&fields=open,high,low,close,volume'
            },
            'GET /api/market-data/mongodb': {
                'description': 'Query market data from MongoDB',
                'parameters': 'Same as QuestDB endpoint',
                'example': '/api/market-data/mongodb?start_time=2024-01-01T00:00:00Z&end_time=2024-01-02T00:00:00Z&tickers=ADANIENT&fields=open,high,low,close,volume'
            },
            'GET /api/market-data/compare': {
                'description': 'Compare performance between QuestDB and MongoDB',
                'parameters': 'Same as other endpoints',
                'returns': 'Performance comparison with query times and speedup analysis'
            },
            'GET /api/health': {
                'description': 'Health check for API and database connections'
            }
        },
        'supported_fields': ['open', 'high', 'low', 'close', 'volume', 'vwap', 'trade_count'],
        'date_format': 'ISO 8601 (e.g., 2024-01-01T00:00:00Z)'
    }
    
    return jsonify(docs)

if __name__ == '__main__':
    print("🚀 Starting Market Data API Server...")
    print("📊 QuestDB endpoint: http://localhost:5000/api/market-data/questdb")
    print("🍃 MongoDB endpoint: http://localhost:5000/api/market-data/mongodb") 
    print("⚡ Compare endpoint: http://localhost:5000/api/market-data/compare")
    print("📖 Documentation: http://localhost:5000/api/docs")
    print("❤️  Health check: http://localhost:5000/api/health")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
