# app/database.py

import sqlite3
import pandas as pd
from pathlib import Path
import streamlit as st
import json


class Database:
    def __init__(self):
        """데이터베이스 초기화"""
        self.DB_PATH = Path("data/reservations.db")
        # data 디렉토리가 없으면 생성
        self.DB_PATH.parent.mkdir(exist_ok=True)
        self.init_db()

    def get_connection(self):
        """데이터베이스 연결 생성"""
        return sqlite3.connect(self.DB_PATH)

    def init_db(self):
        """데이터베이스 테이블 초기화"""
        conn = self.get_connection()
        c = conn.cursor()
        
        # 예약 테이블 생성
        c.execute('''
            CREATE TABLE IF NOT EXISTS reservations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                space TEXT NOT NULL,
                people INTEGER NOT NULL,
                options TEXT,
                price INTEGER NOT NULL,
                name TEXT NOT NULL,
                contact TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 차단된 시간 테이블 생성
        c.execute('''
            CREATE TABLE IF NOT EXISTS blocked_times (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                space TEXT NOT NULL,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()

    def get_all_reservations(self):
        """모든 예약 조회"""
        conn = self.get_connection()
        query = "SELECT * FROM reservations ORDER BY date, time"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df

    def add_reservation(self, data):
        """새로운 예약 추가"""
        conn = self.get_connection()
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO reservations 
            (date, time, space, people, options, price, name, contact)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['date'],
            data['time'],
            data['space'],
            data['people'],
            data['options'],
            data['price'],
            data['name'],
            data['contact']
        ))
        
        conn.commit()
        conn.close()

    def check_availability(self, date, time, space):
        """특정 시간대의 예약 가능 여부 확인"""
        conn = self.get_connection()
        c = conn.cursor()
        
        # 예약 확인
        c.execute('''
            SELECT COUNT(*) FROM reservations 
            WHERE date = ? AND time = ? AND space = ?
        ''', (date, time, space))
        reservation_count = c.fetchone()[0]
        
        # 차단된 시간 확인
        c.execute('''
            SELECT COUNT(*) FROM blocked_times 
            WHERE date = ? AND time = ? AND space = ?
        ''', (date, time, space))
        blocked_count = c.fetchone()[0]
        
        conn.close()
        return reservation_count == 0 and blocked_count == 0

    def block_time(self, date, time, space, reason=''):
        """시간대 차단"""
        conn = self.get_connection()
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO blocked_times (date, time, space, reason)
            VALUES (?, ?, ?, ?)
        ''', (date, time, space, reason))
        
        conn.commit()
        conn.close()

    def get_blocked_times(self):
        """차단된 시간 조회"""
        conn = self.get_connection()
        query = "SELECT * FROM blocked_times ORDER BY date, time"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df

    def reset_database(self):
        """개발용: 데이터베이스 초기화"""
        if st.secrets.get('ENVIRONMENT') == 'development':
            conn = self.get_connection()
            c = conn.cursor()
            c.execute("DROP TABLE IF EXISTS reservations")
            c.execute("DROP TABLE IF EXISTS blocked_times")
            conn.commit()
            conn.close()
            self.init_db()

    def get_day_reservations(self, date):
        """특정 날짜의 예약 조회"""
        conn = self.get_connection()
        query = """
            SELECT time, space 
            FROM reservations 
            WHERE date = ? 
            ORDER BY time
        """
        df = pd.read_sql_query(query, conn, params=[date])
        conn.close()
        return df

    def get_available_times(self, date, space):
        """특정 날짜와 공간의 예약 가능한 시간대 조회"""
        all_times = [f"{i:02d}:00-{i+1:02d}:00" for i in range(9, 22)]
        available_times = []
        
        for time in all_times:
            if self.check_availability(date, time, space):
                available_times.append(time)
        
        return available_times
    
    def get_price_settings(self):
        """가격 설정 조회"""
        conn = self.get_connection()
        c = conn.cursor()
        
        # price_settings 테이블이 없으면 생성
        c.execute('''
            CREATE TABLE IF NOT EXISTS price_settings (
                id INTEGER PRIMARY KEY,
                settings TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 최신 설정 조회
        c.execute('SELECT settings FROM price_settings ORDER BY updated_at DESC LIMIT 1')
        result = c.fetchone()
        
        conn.close()
        
        if result:
            return json.loads(result[0])
        return None
    
    def update_price_settings(self, settings):
        """가격 설정 업데이트"""
        conn = self.get_connection()
        c = conn.cursor()
        
        # price_settings 테이블이 없으면 생성
        c.execute('''
            CREATE TABLE IF NOT EXISTS price_settings (
                id INTEGER PRIMARY KEY,
                settings TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 새로운 설정 저장
        c.execute(
            'INSERT INTO price_settings (settings) VALUES (?)',
            (json.dumps(settings),)
        )
        
        conn.commit()
        conn.close()
    
    