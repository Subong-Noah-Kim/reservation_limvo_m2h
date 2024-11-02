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
    """시간대별 예약 현황 표시 - 세로 버튼 형태"""
    st.markdown("#### 시간대별 예약 현황")
    
    time_slots = [f"{i:02d}:00-{i+1:02d}:00" for i in range(9, 22)]
    
    for time in time_slots:
        is_available = db.check_availability(
            selected_date.strftime('%Y-%m-%d'),
            time,
            space
        )
        
        # 버튼 스타일 정의
        if is_available:
            button_style = """
                padding: 8px 16px;
                background-color: #E8F0FE;
                border-radius: 4px;
                margin: 2px 0;
                text-align: left;
                color: #1f1f1f;
                border: none;
                width: 100%;
                transition: background-color 0.3s;
                cursor: pointer;
                """
            icon = "✅"
        else:
            button_style = """
                padding: 8px 16px;
                background-color: #FFE0E0;
                border-radius: 4px;
                margin: 2px 0;
                text-align: left;
                color: #666666;
                border: none;
                width: 100%;
                cursor: not-allowed;
                """
            icon = "❌"
        
        st.markdown(
            f"""
            <div style='{button_style}'>
                <span style='display: inline-block; min-width: 24px;'>{icon}</span>
                {time}
            </div>
            """,
            unsafe_allow_html=True
        )

def show_reservation_form(db: Database, pc: PriceCalculator):
    """예약 폼 표시"""
    st.title("M2H & LIMVO 공간 예약 시스템")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        show_calendar(
            db, 
            st.session_state.selected_date,
            lambda date: setattr(st.session_state, 'selected_date', date)
        )
    
    with col2:
        # 예약 정보 입력
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
        
        # 가격 즉시 계산 및 표시
        if space and time_slots:
            price = pc.calculate(space, time_slots, people, options)
            st.markdown(
                f"""
                <div style='
                    padding: 16px;
                    background-color: #E8F0FE;
                    border-radius: 8px;
                    margin: 16px 0;
                    text-align: center;
                    font-size: 18px;
                    font-weight: bold;
                '>
                    예상 가격: {format_price(price)}
                </div>
                """,
                unsafe_allow_html=True
            )
        
        # 예약 확정 섹션
        if space and time_slots:
            with st.form("reservation_form", clear_on_submit=True):
                st.markdown("#### 예약자 정보")
                name = st.text_input("예약자 이름")
                contact = st.text_input("연락처")
                
                submit = st.form_submit_button("예약하기")
                
                if submit:
                    if not name or not contact:
                        st.error("예약자 정보를 입력해주세요.")
                    else:
                        try:
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
    
    # 탭에 가격 설정 추가
    tab1, tab2, tab3, tab4 = st.tabs([
        "예약 현황", "시간 차단", "통계", "가격 설정"
    ])
    
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

        # 가격 설정 탭
    with tab4:
        show_price_settings(db, PriceCalculator())

def show_price_settings(db: Database, pc: PriceCalculator):
    """가격 설정 관리 화면"""
    st.markdown("### 가격 설정")
    
    # 기본 가격 설정
    st.markdown("#### 공간별 기본 가격 (시간당)")
    base_prices_cols = st.columns(3)
    
    updated_base_prices = {}
    for idx, (space, price) in enumerate(pc.base_prices.items()):
        with base_prices_cols[idx]:
            updated_base_prices[space] = st.number_input(
                space,
                min_value=0,
                value=price,
                step=1000,
                key=f"base_price_{space}"
            )
    
    # 추가 인원 요금 설정
    st.markdown("#### 추가 인원 요금")
    col1, col2 = st.columns(2)
    with col1:
        base_people = st.number_input(
            "기본 인원 (명)",
            min_value=1,
            value=4,
            key="base_people"
        )
    with col2:
        people_extra_fee = st.number_input(
            "1인당 추가 요금",
            min_value=0,
            value=pc.people_extra_fee,
            step=1000,
            key="people_extra_fee"
        )
    
    # 옵션 요금 설정
    st.markdown("#### 옵션별 추가 요금")
    option_prices_cols = st.columns(3)
    
    updated_option_prices = {}
    for idx, (option, price) in enumerate(pc.option_prices.items()):
        with option_prices_cols[idx]:
            updated_option_prices[option] = st.number_input(
                option,
                min_value=0,
                value=price,
                step=1000,
                key=f"option_price_{option}"
            )
    
    # 가격 시뮬레이션
    st.markdown("#### 가격 시뮬레이션")
    col1, col2 = st.columns(2)
    
    with col1:
        sim_space = st.selectbox("공간 선택", list(updated_base_prices.keys()))
        sim_hours = st.number_input("사용 시간", min_value=1, value=1)
        sim_people = st.number_input("인원", min_value=1, value=1)
    
    with col2:
        sim_options = st.multiselect(
            "추가 옵션",
            list(updated_option_prices.keys())
        )
    
    # 가격 계산
    base_price = updated_base_prices[sim_space] * sim_hours
    people_fee = max(0, (sim_people - base_people)) * people_extra_fee
    option_fee = sum(updated_option_prices[opt] for opt in sim_options)
    total_price = base_price + people_fee + option_fee
    
    # 가격 명세 표시
    st.markdown("#### 가격 명세")
    price_details = f"""
    | 항목 | 금액 |
    |------|------|
    | 기본 요금 ({sim_hours}시간) | {format_price(base_price)} |
    | 추가 인원 요금 | {format_price(people_fee)} |
    | 옵션 요금 | {format_price(option_fee)} |
    | **총 가격** | **{format_price(total_price)}** |
    """
    st.markdown(price_details)
    
    # 설정 저장
    if st.button("가격 설정 저장", type="primary"):
        try:
            # 설정을 파일이나 데이터베이스에 저장
            price_settings = {
                'base_prices': updated_base_prices,
                'base_people': base_people,
                'people_extra_fee': people_extra_fee,
                'option_prices': updated_option_prices
            }
            # price_settings를 JSON 형태로 저장
            db.update_price_settings(price_settings)
            
            # PriceCalculator 업데이트
            pc.base_prices = updated_base_prices
            pc.people_extra_fee = people_extra_fee
            pc.option_prices = updated_option_prices
            
            st.success("가격 설정이 저장되었습니다.")
            
            # 캐시 초기화
            st.cache_data.clear()
            
        except Exception as e:
            st.error(f"저장 중 오류가 발생했습니다: {str(e)}")


def show_admin_login():
    """관리자 로그인 모달"""
    if st.session_state.show_login:
        with st.sidebar:
            st.markdown("### 관리자 로그인")
            with st.form("login_form"):
                password = st.text_input("비밀번호", type="password")
                col1, col2 = st.columns([1,1])
                with col1:
                    if st.form_submit_button("로그인"):
                        if check_password(password):
                            st.session_state.is_admin = True
                            st.session_state.show_login = False
                            st.success("로그인 성공!")
                            st.rerun()
                        else:
                            st.session_state.login_attempts += 1
                            st.error("비밀번호가 일치하지 않습니다.")
                            if st.session_state.login_attempts >= 5:
                                st.error("로그인 시도 횟수를 초과했습니다.")
                with col2:
                    if st.form_submit_button("취소"):
                        st.session_state.show_login = False
                        st.rerun()

def main():
    """메인 애플리케이션"""
    st.set_page_config(
        page_title="M2H & LIMVO 공간 예약 시스템",
        page_icon="🏢",
        layout="wide"
    )
    
    # 세션 상태 초기화
    if 'show_login' not in st.session_state:
        st.session_state.show_login = False
    if 'is_admin' not in st.session_state:
        st.session_state.is_admin = False
    if 'login_attempts' not in st.session_state:
        st.session_state.login_attempts = 0
    if 'selected_date' not in st.session_state:
        st.session_state.selected_date = datetime.now().date()
    if 'current_date' not in st.session_state:
        st.session_state.current_date = datetime.now().date()
    
    # 데이터베이스 및 가격 계산기 초기화
    db = Database()
    pc = PriceCalculator()
    
    # 우측 상단 관리자 버튼
    col1, col2 = st.columns([20, 1])
    with col2:
        if st.session_state.is_admin:
            if st.button("🔓", help="로그아웃"):
                st.session_state.is_admin = False
                st.session_state.login_attempts = 0
                st.rerun()
        else:
            if st.button("🔐", help="관리자 로그인"):
                st.session_state.show_login = True
                st.rerun()
    
    # 관리자 로그인 모달 표시
    if st.session_state.show_login:
        show_admin_login()
    
    # 메인 컨텐츠
    if st.session_state.is_admin:
        show_admin_dashboard(db)
    else:
        show_reservation_form(db, pc)

if __name__ == "__main__":
    main()