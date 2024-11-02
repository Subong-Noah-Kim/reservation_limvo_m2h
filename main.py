import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import calendar
from app.database import Database
from app.models import PriceCalculator
from app.utils import check_password, format_price

# 모바일 감지를 위한 상수
MOBILE_CSS = """
<style>
    @media (max-width: 768px) {
        /* 버튼 크기 조정 */
        .stButton > button {
            width: 100% !important;
            padding: 0.75rem !important;
            font-size: 1rem !important;
            margin: 0.25rem 0 !important;
        }
        
        /* 캘린더 날짜 크기 조정 */
        .calendar-day {
            font-size: 0.9rem !important;
            padding: 0.5rem !important;
            margin: 0.1rem !important;
        }
        
        /* 입력 필드 크기 조정 */
        .stTextInput > div > div > input {
            font-size: 1rem !important;
            padding: 0.5rem !important;
        }
        
        /* 선택 박스 크기 조정 */
        .stSelectbox > div > div > select {
            font-size: 1rem !important;
            padding: 0.5rem !important;
        }
        
        /* 여백 조정 */
        .block-container {
            padding: 1rem !important;
        }
        
        /* 헤더 텍스트 크기 조정 */
        h1 {
            font-size: 1.5rem !important;
        }
        
        h2, h3 {
            font-size: 1.2rem !important;
        }
        
        /* 시간 슬롯 버튼 크기 조정 */
        .time-slot {
            padding: 0.75rem !important;
            margin: 0.25rem 0 !important;
            font-size: 0.9rem !important;
        }
        
        /* 멀티셀렉트 크기 조정 */
        .stMultiSelect > div > div > div {
            font-size: 1rem !important;
            padding: 0.5rem !important;
        }
        
        /* 날짜 선택기 크기 조정 */
        .stDateInput > div > div > input {
            font-size: 1rem !important;
            padding: 0.5rem !important;
        }
    }
</style>
"""

def is_mobile():
    """모바일 여부 확인"""
    # 기본 너비를 체크하여 모바일 여부 판단
    return st.session_state.get('mobile_width', 1000) < 768

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
    if 'mobile_width' not in st.session_state:
        st.session_state.mobile_width = 1000

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
    
    # 월 선택 컨트롤 - 모바일에서는 더 큰 버튼
    col1, col2, col3 = st.columns([1,2,1])
    
    with col1:
        if st.button("◀", key="prev_month", use_container_width=True):
            if "current_date" in st.session_state:
                st.session_state.current_date = (st.session_state.current_date.replace(day=1) - timedelta(days=1)).replace(day=1)
    
    with col2:
        current_date = st.session_state.current_date
        st.markdown(f"<div style='text-align:center; font-size: {'1.1rem' if is_mobile() else '1.3rem'};'><b>{current_date.year}년 {current_date.month}월</b></div>", unsafe_allow_html=True)
    
    with col3:
        if st.button("▶", key="next_month", use_container_width=True):
            if "current_date" in st.session_state:
                next_month = st.session_state.current_date.replace(day=1)
                st.session_state.current_date = (next_month + timedelta(days=32)).replace(day=1)
    
    # 캘린더 표시
    calendar_data = get_month_calendar(current_date.year, current_date.month, db)
    
    # 요일 헤더 - 모바일에서는 작은 글씨
    cols = st.columns(7)
    days = ['월', '화', '수', '목', '금', '토', '일']
    for i, day in enumerate(days):
        cols[i].markdown(
            f"<div style='text-align:center; font-size: {'0.8rem' if is_mobile() else '1rem'};'><b>{day}</b></div>",
            unsafe_allow_html=True
        )
    
    # 날짜 표시 - 모바일에서는 작은 버튼
    for week in calendar_data:
        cols = st.columns(7)
        for i, day_data in enumerate(week):
            if day_data["day"] == "":
                cols[i].write("")
            else:
                day = day_data["day"]
                reservations = day_data["reservations"]
                date_obj = date(current_date.year, current_date.month, day)
                
                button_style = """
                    text-align: center;
                    padding: {}rem;
                    font-size: {}rem;
                """.format(
                    "0.3" if is_mobile() else "0.5",
                    "0.8" if is_mobile() else "1"
                )
                
                if date_obj < datetime.now().date():
                    cols[i].markdown(
                        f"<div style='{button_style} color:gray;'>{day}</div>",
                        unsafe_allow_html=True
                    )
                elif date_obj == selected_date:
                    cols[i].markdown(
                        f"<div style='{button_style} background-color:#F63366; color:white; border-radius:5px;'>{day}</div>",
                        unsafe_allow_html=True
                    )
                else:
                    if cols[i].button(f"{day}", key=f"day_{day}", use_container_width=True):
                        on_date_select(date_obj)
                
                if reservations > 0:
                    cols[i].markdown(
                        f"<div style='text-align:center; color:#F63366; font-size: {'0.7rem' if is_mobile() else '0.9rem'};'>{reservations}건</div>",
                        unsafe_allow_html=True
                    )

def show_time_slots(db, selected_date, space):
    """시간대별 예약 현황 표시 - 모바일 최적화"""
    st.markdown("#### 시간대별 예약 현황")
    
    time_slots = [f"{i:02d}:00-{i+1:02d}:00" for i in range(9, 22)]
    
    # 모바일에서는 한 열로, PC에서는 두 열로
    if is_mobile():
        for time in time_slots:
            is_available = db.check_availability(
                selected_date.strftime('%Y-%m-%d'),
                time,
                space
            )
            show_time_slot_button(time, is_available)
    else:
        col1, col2 = st.columns(2)
        mid_point = len(time_slots) // 2
        
        with col1:
            for time in time_slots[:mid_point]:
                is_available = db.check_availability(
                    selected_date.strftime('%Y-%m-%d'),
                    time,
                    space
                )
                show_time_slot_button(time, is_available)
        
        with col2:
            for time in time_slots[mid_point:]:
                is_available = db.check_availability(
                    selected_date.strftime('%Y-%m-%d'),
                    time,
                    space
                )
                show_time_slot_button(time, is_available)

def show_time_slot_button(time, is_available):
    """시간 슬롯 버튼 표시"""
    button_style = f"""
        padding: {0.5 if is_mobile() else 0.75}rem;
        background-color: {"#E8F0FE" if is_available else "#FFE0E0"};
        border-radius: 4px;
        margin: 2px 0;
        text-align: left;
        color: {"#1f1f1f" if is_available else "#666666"};
        border: none;
        width: 100%;
        font-size: {0.9 if is_mobile() else 1}rem;
        cursor: {"pointer" if is_available else "not-allowed"};
    """
    icon = "✅" if is_available else "❌"
    st.markdown(
        f"<div style='{button_style}'><span style='display: inline-block; min-width: 24px;'>{icon}</span>{time}</div>",
        unsafe_allow_html=True
    )

def show_reservation_form(db: Database, pc: PriceCalculator):
    """예약 폼 표시"""
    st.title("M2H & LIMVO 공간 예약 시스템")
    
    if is_mobile():
        # 모바일 레이아웃 - 단일 컬럼
        show_calendar(
            db, 
            st.session_state.selected_date,
            lambda date: setattr(st.session_state, 'selected_date', date)
        )
        
        st.markdown("---")  # 구분선
        
        space = st.selectbox(
            "공간 선택",
            ["연습실A", "연습실B", "스튜디오"],
            key="mobile_space"
        )
        
        st.markdown(f"**선택된 날짜: {st.session_state.selected_date.strftime('%Y-%m-%d')}**")
        
        # 예약 가능한 시간대 표시
        show_time_slots(db, st.session_state.selected_date, space)
        
        # 예약 가능한 시간대 필터링
        available_times = [
            time for time in [f"{i:02d}:00-{i+1:02d}:00" for i in range(9, 22)]
            if db.check_availability(
                st.session_state.selected_date.strftime('%Y-%m-%d'),
                time,
                space
            )
        ]
        
        with st.container():
            time_slots = st.multiselect("예약 시간 선택", available_times)
            people = st.number_input("인원", min_value=1, max_value=10, value=1)
            options = st.multiselect(
                "추가 옵션",
                ["음향장비", "조명장비", "악기대여"]
            )
            
            # 가격 표시
            if space and time_slots:
                price = pc.calculate(space, time_slots, people, options)
                st.markdown(
                    f"""
                    <div style='
                        padding: 1rem;
                        background-color: #E8F0FE;
                        border-radius: 8px;
                        margin: 1rem 0;
                        text-align: center;
                        font-size: {1.1 if is_mobile() else 1.3}rem;
                        font-weight: bold;
                    '>
                        예상 가격: {format_price(price)}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            
            # 예약자 정보
            if space and time_slots:
                with st.form("mobile_reservation_form", clear_on_submit=True):
                    st.markdown("#### 예약자 정보")
                    name = st.text_input("예약자 이름")
                    contact = st.text_input("연락처")
                    
                    submit = st.form_submit_button("예약하기", use_container_width=True)
                    
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
    
    else:
        # PC 레이아웃 - 2열
        col1, col2 = st.columns([2, 1])
        
        with col1:
            show_calendar(
                db, 
                st.session_state.selected_date,
                lambda date: setattr(st.session_state, 'selected_date', date)
            )
        
        with col2:
            space = st.selectbox(
                "공간 선택",
                ["연습실A", "연습실B", "스튜디오"]
            )
            
            st.markdown(f"**선택된 날짜: {st.session_state.selected_date.strftime('%Y-%m-%d')}**")
            
            show_time_slots(db, st.session_state.selected_date, space)
            
            available_times = [
                time for time in [f"{i:02d}:00-{i+1:02d}:00" for i in range(9, 22)]
                if db.check_availability(
                    st.session_state.selected_date.strftime('%Y-%m-%d'),
                    time,
                    space
                )
            ]
            
            time_slots = st.multiselect("예약 시간 선택", available_times)
            people = st.number_input("인원", min_value=1, max_value=10, value=1)
            options = st.multiselect(
                "추가 옵션",
                ["음향장비", "조명장비", "악기대여"]
            )
            
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
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "예약 현황", "시간 차단", "통계", "가격 설정"
    ])
    
    # 예약 현황 탭
    with tab1:
        reservations = db.get_all_reservations()
        if not reservations.empty:
            st.dataframe(reservations, use_container_width=True)
            csv = reservations.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                "예약 데이터 다운로드",
                csv,
                "reservations.csv",
                "text/csv",
                use_container_width=is_mobile()
            )
        else:
            st.info("예약 내역이 없습니다.")
    
    # 시간 차단 탭
    with tab2:
        if is_mobile():
            with st.form("block_time_form_mobile"):
                block_date = st.date_input("차단할 날짜", min_value=datetime.now().date())
                block_space = st.selectbox("차단할 공간", ["연습실A", "연습실B", "스튜디오"])
                block_times = st.multiselect(
                    "차단할 시간",
                    [f"{i:02d}:00-{i+1:02d}:00" for i in range(9, 22)]
                )
                reason = st.text_input("차단 사유")
                
                if st.form_submit_button("차단하기", use_container_width=True):
                    handle_block_time(db, block_date, block_space, block_times, reason)
            
            st.markdown("#### 차단된 시간")
            show_blocked_times(db)
        else:
            col1, col2 = st.columns(2)
            with col1:
                with st.form("block_time_form"):
                    block_date = st.date_input("차단할 날짜", min_value=datetime.now().date())
                    block_space = st.selectbox("차단할 공간", ["연습실A", "연습실B", "스튜디오"])
                    block_times = st.multiselect(
                        "차단할 시간",
                        [f"{i:02d}:00-{i+1:02d}:00" for i in range(9, 22)]
                    )
                    reason = st.text_input("차단 사유")
                    
                    if st.form_submit_button("차단하기"):
                        handle_block_time(db, block_date, block_space, block_times, reason)
            
            with col2:
                st.markdown("#### 차단된 시간")
                show_blocked_times(db)
    
    # 통계 탭
    with tab3:
        if not db.get_all_reservations().empty:
            if is_mobile():
                start_date = st.date_input(
                    "시작일",
                    value=datetime.now().date() - timedelta(days=30)
                )
                end_date = st.date_input("종료일", value=datetime.now().date())
            else:
                col1, col2 = st.columns(2)
                with col1:
                    start_date = st.date_input(
                        "시작일",
                        value=datetime.now().date() - timedelta(days=30)
                    )
                with col2:
                    end_date = st.date_input("종료일", value=datetime.now().date())
            
            show_statistics(db, start_date, end_date)
    
    # 가격 설정 탭
    with tab4:
        show_price_settings(db, PriceCalculator())

def handle_block_time(db, block_date, block_space, block_times, reason):
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

def show_blocked_times(db):
    blocked_times = db.get_blocked_times()
    if not blocked_times.empty:
        st.dataframe(blocked_times, use_container_width=True)
    else:
        st.info("차단된 시간이 없습니다.")

def show_statistics(db, start_date, end_date):
    reservations = db.get_all_reservations()
    reservations['date'] = pd.to_datetime(reservations['date'])
    filtered = reservations[
        (reservations['date'].dt.date >= start_date) &
        (reservations['date'].dt.date <= end_date)
    ]
    
    if not filtered.empty:
        total_revenue = filtered['price'].sum()
        total_count = len(filtered)
        avg_price = total_revenue / total_count if total_count > 0 else 0
        
        if is_mobile():
            # 모바일에서는 세로로 배치
            st.metric("총 매출", format_price(total_revenue))
            st.metric("총 예약 수", total_count)
            st.metric("평균 예약 가격", format_price(avg_price))
        else:
            # PC에서는 3열로 배치
            col1, col2, col3 = st.columns(3)
            col1.metric("총 매출", format_price(total_revenue))
            col2.metric("총 예약 수", total_count)
            col3.metric("평균 예약 가격", format_price(avg_price))
        
        # 공간별 통계
        st.markdown("#### 공간별 통계")
        space_stats = filtered.groupby('space').agg({
            'id': 'count',
            'price': 'sum'
        }).rename(columns={'id': '예약 수', 'price': '매출'})
        st.dataframe(space_stats, use_container_width=True)
    else:
        st.info("선택한 기간에 예약 데이터가 없습니다.")

def show_price_settings(db: Database, pc: PriceCalculator):
    """가격 설정 관리 화면"""
    st.markdown("### 가격 설정")
    
    if is_mobile():
        # 모바일 레이아웃 - 한 열로 표시
        st.markdown("#### 공간별 기본 가격 (시간당)")
        for space, price in pc.base_prices.items():
            updated_base_prices[space] = st.number_input(
                space,
                min_value=0,
                value=price,
                step=1000,
                key=f"base_price_{space}",
                use_container_width=True
            )
        
        st.markdown("#### 추가 인원 요금")
        base_people = st.number_input(
            "기본 인원 (명)",
            min_value=1,
            value=4,
            key="base_people"
        )
        people_extra_fee = st.number_input(
            "1인당 추가 요금",
            min_value=0,
            value=pc.people_extra_fee,
            step=1000,
            key="people_extra_fee"
        )
        
        st.markdown("#### 옵션별 추가 요금")
        for option, price in pc.option_prices.items():
            updated_option_prices[option] = st.number_input(
                option,
                min_value=0,
                value=price,
                step=1000,
                key=f"option_price_{option}"
            )
    else:
        # PC 레이아웃 - 여러 열로 표시
        st.markdown("#### 공간별 기본 가격 (시간당)")
        base_prices_cols = st.columns(3)
        for idx, (space, price) in enumerate(pc.base_prices.items()):
            with base_prices_cols[idx]:
                updated_base_prices[space] = st.number_input(
                    space,
                    min_value=0,
                    value=price,
                    step=1000,
                    key=f"base_price_{space}"
                )
        
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
        
        st.markdown("#### 옵션별 추가 요금")
        option_prices_cols = st.columns(3)
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
    if is_mobile():
        sim_space = st.selectbox("공간 선택", list(updated_base_prices.keys()))
        sim_hours = st.number_input("사용 시간", min_value=1, value=1)
        sim_people = st.number_input("인원", min_value=1, value=1)
        sim_options = st.multiselect("추가 옵션", list(updated_option_prices.keys()))
    else:
        col1, col2 = st.columns(2)
        with col1:
            sim_space = st.selectbox("공간 선택", list(updated_base_prices.keys()))
            sim_hours = st.number_input("사용 시간", min_value=1, value=1)
            sim_people = st.number_input("인원", min_value=1, value=1)
        with col2:
            sim_options = st.multiselect("추가 옵션", list(updated_option_prices.keys()))
    
    # 가격 계산 및 표시
    base_price = updated_base_prices[sim_space] * sim_hours
    people_fee = max(0, (sim_people - base_people)) * people_extra_fee
    option_fee = sum(updated_option_prices[opt] for opt in sim_options)
    total_price = base_price + people_fee + option_fee
    
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
    
    # 설정 저장 버튼
    if st.button("가격 설정 저장", type="primary", use_container_width=is_mobile()):
        try:
            price_settings = {
                'base_prices': updated_base_prices,
                'base_people': base_people,
                'people_extra_fee': people_extra_fee,
                'option_prices': updated_option_prices
            }
            db.update_price_settings(price_settings)
            pc.update_settings(price_settings)
            st.success("가격 설정이 저장되었습니다.")
            st.cache_data.clear()
        except Exception as e:
            st.error(f"저장 중 오류가 발생했습니다: {str(e)}")

def main():
    """메인 애플리케이션"""
    st.set_page_config(
        page_title="M2H & LIMVO 공간 예약 시스템",
        page_icon="🏢",
        layout="wide"
    )
    
    # CSS 스타일 추가
    st.markdown(MOBILE_CSS, unsafe_allow_html=True)
    
    # 화면 너비 감지를 위한 JavaScript 삽입
    st.markdown("""
        <script>
            var width = window.innerWidth;
            if (width !== undefined) {
                window.parent.postMessage({type: 'streamlit:setComponentValue', value: width}, '*');
            }
        </script>
        """, unsafe_allow_html=True)
    
    # 세션 상태 초기화
    init_session_state()
    
    # 데이터베이스 및 가격 계산기 초기화
    db = Database()
    pc = PriceCalculator()
    
    # 우측 상단 관리자 버튼
    col1, col2 = st.columns([20, 1])
    with col2:
        if st.session_state.is_admin:
            if st.button("🔓", help="로그아웃", use_container_width=True):
                st.session_state.is_admin = False
                st.session_state.login_attempts = 0
                st.rerun()
        else:
            if st.button("🔐", help="관리자 로그인", use_container_width=True):
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