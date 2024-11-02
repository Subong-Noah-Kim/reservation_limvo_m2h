# app/models.py
class PriceCalculator:
    def __init__(self):
        self.base_prices = {
            '연습실A': 10000,
            '연습실B': 15000,
            '스튜디오': 30000
        }
        self.option_prices = {
            '음향장비': 5000,
            '조명장비': 8000,
            '악기대여': 10000
        }
        self.people_extra_fee = 2000

    def calculate(self, space, time_slots, people, options):
        """가격 계산"""
        # 기본 가격 계산
        base = self.base_prices[space] * len(time_slots)
        
        # 인원 추가 요금
        people_fee = max(0, (people - 4)) * self.people_extra_fee
        
        # 옵션 요금
        option_fee = sum(self.option_prices[opt] for opt in options)
        
        return base + people_fee + option_fee