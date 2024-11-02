import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import calendar
from app.database import Database
from app.models import PriceCalculator
from app.utils import check_password, format_price

def init_session_state():
    """세션 상태 초기화"""
    if 'is_admin' not in st.session_state:
        st.session_state.is_admin = False
    if 'login_attempts' not in st.session_state:
        st.session_state.login_attempts = 0
    if 'selected_date' not in st.session_state:
        st.session_state.selected_date = datetime.now().date()
    if 'current_date' not in st.session_state:
        st.session_state.current_date = datetime.now().date()

def get_month_calendar(year, month, db):
    """해당 월의 캘린더 데이터 생성"""
    cal = calendar.monthcalendar(year, month)
    month_data = []
    
    for week in cal:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append({"day": "", "reservations": 0})
            else:
                date_str = f"{year}-{month:02d}-{day:02d}"
                # 해당 날짜의 예약 수 조회
                reservations = len(db.get_day_reservations(date_str))
                week_data.append({
                    "day": day,
                    "reservations": reservations
                })
        month_data.append(week_data)
    
    return month_data

def show_calendar(db, selected_date, on_date_select):
    """캘린더 표시"""
    st.markdown("### 예약 캘린더")
    
    # 월 선택 컨트롤
    col1, col2, col3 = st.columns([1,3,1])
    
    with col1:
        if st.button("◀"):
            if "current_date" in st.session_state:
                st.session_state.current_date = (st.session_state.current_date.replace(day=1) - timedelta(days=1)).replace(day=1)
    
    with col2:
        current_date = st.session_state.current_date
        st.markdown(f"#### {current_date.year}년 {current_date.month}월")
    
    with col3:
        if st.button("▶"):
            if "current_date" in st.session_state:
                next_month = st.session_state.current_date.replace(day=1)
                st.session_state.current_date = (next_month + timedelta(days=32)).replace(day=1)
    
    # 캘린더 표시
    calendar_data = get_month_calendar(current_date.year, current_date.month, db)
    
    # 요일 헤더
    cols = st.columns(7)
    for i, day in enumerate(['월', '화', '수', '목', '금', '토', '일']):
        cols[i].markdown(f"<div style='text-align:center'><b>{day}</b></div>", unsafe_allow_html=True)
    
    # 날짜 표시
    for week in calendar_data:
        cols = st.columns(7)
        for i, day_data in enumerate(week):
            if day_data["day"] == "":
                cols[i].write("")
            else:
                day = day_data["day"]
                reservations = day_data["reservations"]
                date_obj = date(current_date.year, current_date.month, day)
                
                # 날짜 버튼 스타일링
                if date_obj < datetime.now().date():
                    cols[i].markdown(f"<div style='text-align:center; color:gray;'>{day}</div>", unsafe_allow_html=True)
                elif date_obj == selected_date:
                    cols[i].markdown(f"<div style='text-align:center; padding:5px; background-color:#F63366; color:white; border-radius:5px;'>{day}</div>", unsafe_allow_html=True)
                else:
                    if cols[i].button(f"{day}", key=f"day_{day}", use_container_width=True):
                        on_date_select(date_obj)
                
                # 예약 건수 표시
                if reservations > 0:
                    cols[i].markdown(f"<div style='text-align:center; color:#F63366;'>{reservations}건</div>", unsafe_allow_html=True)

def show_time_slots(db, selected_date, space):
    """시간대별 예약 현황 표시"""
    time_slots = [f"{i:02d}:00-{i+1:02d}:00" for i in range(9, 22)]
    
    st.markdown("#### 시간대별 예약 현황")
    
    # 4열 그리드로 시간대 표시
    cols = st.columns(4)
    for idx, time in enumerate(time_slots):
        col_idx = idx % 4
        is_available = db.check_availability(
            selected_date.strftime('%Y-%m-%d'),
            time,
            space
        )
        
        style = "background-color:#E8F0FE;" if is_available else "background-color:#FFE0E0;"
        icon = "✅" if is_available else "❌"
        
        cols[col_idx].markdown(
            f"<div style='padding:8px; {style} border-radius:5px; margin:2px 0; text-align:center'>"
            f"{icon} {time}</div>",
            unsafe_allow_html=True
        )

def show_reservation_form(db: Database, pc: PriceCalculator):
    """예약 폼 표시"""
    st.title("공간 예약 시스템")
    
    # 2단 레이아웃
    col1, col2 = st.columns([2, 1])
    
    with col1:
        show_calendar(
            db, 
            st.session_state.selected_date,
            lambda date: setattr(st.session_state, 'selected_date', date)
        )
    
    with col2:
        with st.form("reservation_form", clear_on_submit=True):
            space = st.selectbox(
                "공간 선택",
                ["연습실A", "연습실B", "스튜디오"]
            )
            
            st.markdown(f"**선택된 날짜: {st.session_state.selected_date.strftime('%Y-%m-%d')}**")
            
            # 예약 가능한 시간대 표시
            show_time_slots(db, st.session_state.selected_date, space)
            
            # 예약 가능한 시간대만 선택 가능하도록 필터링
            available_times = []
            for time in [f"{i:02d}:00-{i+1:02d}:00" for i in range(9, 22)]:
                if db.check_availability(
                    st.session_state.selected_date.strftime('%Y-%m-%d'),
                    time,
                    space
                ):
                    available_times.append(time)
            
            time_slots = st.multiselect("예약 시간 선택", available_times)
            people = st.number_input("인원", min_value=1, max_value=10, value=1)
            options = st.multiselect(
                "추가 옵션",
                ["음향장비", "조명장비", "악기대여"]
            )
            
            # 예약자 정보
            name = st.text_input("예약자 이름")
            contact = st.text_input("연락처")
            
            # 가격 계산 및 표시
            if time_slots:
                price = pc.calculate(space, time_slots, people, options)
                st.info(f"예상 가격: {format_price(price)}")
            
            # 예약 버튼
            submit = st.form_submit_button("예약하기")
            
            if submit:
                if not time_slots:
                    st.error("예약 시간을 선택해주세요.")
                elif not name or not contact:
                    st.error("예약자 정보를 입력해주세요.")
                else:
                    try:
                        # 예약 처리
                        for time in time_slots:
                            db.add_reservation({
                                'date': st.session_state.selected_date.strftime('%Y-%m-%d'),
                                'time': time,
                                'space': space,
                                'people': people,
                                'options': ','.join(options),
                                'price': price // len(time_slots),
                                'name': name,
                                'contact': contact
                            })
                        st.success("예약이 완료되었습니다!")
                        st.balloons()
                    except Exception as e:
                        st.error("예약 처리 중 오류가 발생했습니다.")
                        print(f"Error: {e}")

def show_admin_dashboard(db: Database):
    """관리자 대시보드 표시"""
    st.title("관리자 대시보드")
    
    tab1, tab2, tab3 = st.tabs(["예약 현황", "시간 차단", "통계"])
    
    # 예약 현황 탭
    with tab1:
        reservations = db.get_all_reservations()
        if not reservations.empty:
            st.dataframe(reservations)
            
            # CSV 다운로드
            csv = reservations.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                "예약 데이터 다운로드",
                csv,
                "reservations.csv",
                "text/csv"
            )
        else:
            st.info("예약 내역이 없습니다.")
    
    # 시간 차단 탭
    with tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            with st.form("block_time_form"):
                block_date = st.date_input(
                    "차단할 날짜",
                    min_value=datetime.now().date()
                )
                block_space = st.selectbox(
                    "차단할 공간",
                    ["연습실A", "연습실B", "스튜디오"]
                )
                block_times = st.multiselect(
                    "차단할 시간",
                    [f"{i:02d}:00-{i+1:02d}:00" for i in range(9, 22)]
                )
                reason = st.text_input("차단 사유")
                
                if st.form_submit_button("차단하기"):
                    if block_times:
                        for time in block_times:
                            db.block_time(
                                block_date.strftime('%Y-%m-%d'),
                                time,
                                block_space,
                                reason
                            )
                        st.success("선택한 시간이 차단되었습니다.")
                    else:
                        st.error("차단할 시간을 선택해주세요.")
        
        with col2:
            st.markdown("#### 차단된 시간")
            blocked_times = db.get_blocked_times()
            if not blocked_times.empty:
                st.dataframe(blocked_times)
            else:
                st.info("차단된 시간이 없습니다.")
    
    # 통계 탭
    with tab3:
        if not db.get_all_reservations().empty:
            # 기간 선택
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input(
                    "시작일",
                    value=datetime.now().date() - timedelta(days=30)
                )
            with col2:
                end_date = st.date_input("종료일", value=datetime.now().date())
            
            # 통계 계산
            reservations = db.get_all_reservations()
            reservations['date'] = pd.to_datetime(reservations['date'])
            filtered = reservations[
                (reservations['date'].dt.date >= start_date) &
                (reservations['date'].dt.date <= end_date)
            ]
            
            if not filtered.empty:
                col1, col2, col3 = st.columns(3)
                # 전체 통계
                total_revenue = filtered['price'].sum()
                total_count = len(filtered)
                avg_price = total_revenue / total_count if total_count > 0 else 0
                
                col1.metric("총 매출", format_price(total_revenue))
                col2.metric("총 예약 수", total_count)
                col3.metric("평균 예약 가격", format_price(avg_price))
                
                # 공간별 통계
                st.markdown("#### 공간별 통계")
                space_stats = filtered.groupby('space').agg({
                    'id': 'count',
                    'price': 'sum'
                }).rename(columns={'id': '예약 수', 'price': '매출'})
                st.dataframe(space_stats)
            else:
                st.info("선택한 기간에 예약 데이터가 없습니다.")

def main():
    st.set_page_config(
        page_title="공간 예약 시스템",
        page_icon="🏢",
        layout="wide"
    )
    
    # 세션 상태 초기화
    init_session_state()
    
    # 데이터베이스 및 가격 계산기 초기화
    db = Database()
    pc = PriceCalculator()
    
    # 관리자 로그인 사이드바
    with st.sidebar:
        if not st.session_state.is_admin:
            st.subheader("관리자 로그인")
            with st.form("login_form"):
                password = st.text_input("비밀번호", type="password")
                if st.form_submit_button("로그인"):
                    if check_password(password):
                        st.session_state.is_admin = True
                        st.success("로그인 성공!")
                        st.rerun()
                    else:
                        st.session_state.login_attempts += 1
                        st.error("비밀번호가 일치하지 않습니다.")
                        if st.session_state.login_attempts >= 5:
                            st.error("로그인 시도 횟수를 초과했습니다.")
        else:
            st.success("관리자로 로그인됨")
            if st.button("로그아웃"):
                st.session_state.is_admin = False
                st.session_state.login_attempts = 0

def main():
    st.set_page_config(
        page_title="공간 예약 시스템",
        page_icon="🏢",
        layout="wide"
    )
    
    # 세션 상태 초기화
    init_session_state()
    
    # 데이터베이스 및 가격 계산기 초기화
    db = Database()
    pc = PriceCalculator()
    
    # 관리자 로그인 사이드바
    with st.sidebar:
        if not st.session_state.is_admin:
            st.subheader("관리자 로그인")
            with st.form("login_form"):
                password = st.text_input("비밀번호", type="password")
                if st.form_submit_button("로그인"):
                    if check_password(password):
                        st.session_state.is_admin = True
                        st.success("로그인 성공!")
                        st.rerun()
                    else:
                        st.session_state.login_attempts += 1
                        st.error("비밀번호가 일치하지 않습니다.")
                        if st.session_state.login_attempts >= 5:
                            st.error("로그인 시도 횟수를 초과했습니다.")
        else:
            st.success("관리자로 로그인됨")
            if st.button("로그아웃"):
                st.session_state.is_admin = False
                st.session_state.login_attempts = 0
                st.rerun()
    
    # 메인 컨텐츠
    if st.session_state.is_admin:
        show_admin_dashboard(db)
    else:
        show_reservation_form(db, pc)

if __name__ == "__main__":
    main()