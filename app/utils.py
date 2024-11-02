# app/utils.py
import hashlib
import streamlit as st

def check_password(password):
    """비밀번호 확인"""
    return hashlib.sha256(password.encode()).hexdigest() == st.secrets["ADMIN_PASSWORD_HASH"]

def format_price(price):
    """가격 포맷팅"""
    return f"{price:,}원"