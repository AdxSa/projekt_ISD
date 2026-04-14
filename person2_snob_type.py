import os
import numpy as np
import pandas as pd
from scipy.stats import norm, randint, poisson, bernoulli
from datetime import datetime, timedelta
from dynamic_copula import generate_dynamic_copula_data
import random
import time
import math

class SnobDataPool:
    _data = None
    _FILE_PATH = "snob_base_profiles.csv"

    @classmethod
    def get_data(cls, data_size=10000):
        if cls._data is not None and data_size != 1:
            return cls._data

        if os.path.exists(cls._FILE_PATH):
            cls._data = pd.read_csv(cls._FILE_PATH)
        else:

            target_matrix = np.array([
                [1.0,  -0.1, -0.2, -0.3],
                [-0.1,  1.0,  0.2,  0.1],
                [-0.2, 0.2,  1.0,  0.4],
                [-0.3, 0.1,  0.4,  1.0]
            ])

            ppfs = [
                lambda u: norm(loc=15000, scale=4000).ppf(u),
                lambda u: 1 + bernoulli(p=0.7).ppf(u),
                lambda u: poisson(mu=2).ppf(u) + 1,
                lambda u: np.where(
                    u < 0.6,
                    norm(loc=7, scale=3).ppf(u / 0.6),      # albo last-minute
                    norm(loc=30, scale=10).ppf((u - 0.6) / 0.4)   # albo z wyprzedzeniem
                )
            ]

            cls._data = generate_dynamic_copula_data(
                target_matrix,
                ppfs,
                ["income", "guests", "days_to_stay", "days_to_vacation"],
                num_samples=data_size
            )

            cls._data['income'] = cls._data['income'].clip(lower=5000)
            cls._data['days_to_vacation'] = cls._data['days_to_vacation'].clip(lower=1)

            cls._data.to_csv(cls._FILE_PATH, index=False)

        return cls._data

    @classmethod
    def sample_base_profile(cls):
        return cls.get_data().sample(1).iloc[0].to_dict()

class BasePerson_Snob:
    def __init__(self):
        self.name = 'Snob'
        self.description = "Zamożny, wymagający, bezdzietny, często last-minute"
        self.base_profile = None
        self._public_data = None

    def generate_requests(self, current_date: str) -> dict:
        if self._public_data:
            return self._public_data
        else:
            self._get_info(current_date)
            return self._public_data

    def decide(self, offers: list[dict]) -> str | None:

            if not offers:
                return {
                    "offer_id": None,
                    "decision": "decline"
                }

            guests = self._public_data["guests"]
            days = int(self.base_profile['days_to_stay'])
            days_to_vacation = self.base_profile['days_to_vacation']
            returning_client = self._context["returning_client"]

            max_budget_per_person_per_day = self._hidden_data["max_budget_per_person_per_day"]
            get_up_with_left_foot = self._hidden_data["get_up_with_left_foot"]
            is_vacation_time_strictly_locked = self._hidden_data["is_vacation_time_strictly_locked"]

            offers_utility = {}

            for offer in offers:
                price = offer.get("price", 1000)
                price_per_person_per_day = price / (guests * days)
                price_ratio = price_per_person_per_day / max_budget_per_person_per_day

                U = 0

                if get_up_with_left_foot:
                    U -= 1

                # efekt snoba (premium sweet spot)
                if price_ratio < 0.7:
                    U -= 1.5 # za tanie = podejrzane
                elif price_ratio > 1.3:
                    U -= 2.0 # za drogie = odpada
                else:
                    U += 2.0 # w sam raz

                # jeśli powraca = wcześniej mu się podobało = może zapłacić więcej
                if returning_client:
                    U += 2.5

                # brak czasu na zmianę planów mocno podbija użyteczność
                if is_vacation_time_strictly_locked: # nienegocjowalny termin = większa panika
                    max_urgency = 2.5
                    decay_rate = 0.05
                    w_urgency = max_urgency * np.exp(-decay_rate * days_to_vacation)
                    U += w_urgency
                else:
                    max_urgency = 2.5
                    decay_rate = 0.13
                    w_urgency = max_urgency * np.exp(-decay_rate * days_to_vacation)
                    U += w_urgency

                # wrażliwość weekendowa
                checkin_date = datetime.strptime(self._public_data["checkin"], "%Y-%m-%d")

                weekend_penalty = 0.0

                is_flexible = not is_vacation_time_strictly_locked

                if days <= 3 and is_flexible:

                    has_weekend = False

                    # sprawdzamy każdy dzień pobytu
                    for i in range(days):
                        current_day = checkin_date + timedelta(days=i)
                        day_of_week = current_day.weekday()

                        if day_of_week in [5, 6]:  # sobota, niedziela
                            has_weekend = True
                            break

                    if has_weekend:
                        weekend_penalty = -1.0  # snob nie lubi tłumów i dzieci
                    else:
                        weekend_penalty = +0.3  # bonus za ciszę

                U += weekend_penalty

                offers_utility[offer.get("offer_id")] = U

            best_offer = max(offers_utility.items(), key=lambda x: x[1])

            p_accept = 1 / (1 + math.exp(-best_offer[1]))

            if random.random() < p_accept:
                return {
                    "offer_id": best_offer[0],
                    "decision": "accept"
                }
            else:
                return {"offer_id": None,
                        "decision": "decline"
                }

    def _get_info(self, current_date: str) -> tuple[dict, dict, dict]:

        current_date_date = datetime.strptime(current_date, "%Y-%m-%d")

        # 1. Pobierz bazowe zmienne skorelowane z puli.
        self.base_profile = SnobDataPool.sample_base_profile()

        guests = int(self.base_profile['guests'])
        days_to_stay = int(self.base_profile['days_to_stay'])
        days_to_vacation = int(self.base_profile['days_to_vacation'])
        total_income = self.base_profile['income']

        if guests == 1:
            base_room = "single"
            suite_prob = 0.6 if total_income > 20000 else 0.4
        else: # Jeśli osoba towarzysząca -> chęć zaimponowania -> częstszy suite
            base_room = "double"
            suite_prob = 0.7 if total_income > 15000 else 0.5

        if random.random() < suite_prob:
            room_type = "suite"
        else:
            room_type = base_room

        # 2. Oblicz Daty
        checkin = current_date_date + timedelta(days=days_to_vacation)
        checkout = checkin + timedelta(days=days_to_stay)

        # 3. Zmienne pochodne (logika biznesowa)
        monthly_income_per_person = total_income / guests

        total_trip_budget = total_income * 0.6 # cecha snoba - rozrzutny
        budget_per_person_per_day = total_trip_budget / (guests * days_to_stay)

        # Śniadanie -> często biorą
        prob_breakfast = min(0.95, max(0.5, (budget_per_person_per_day / 300)))  # Skalujemy prawdopodobieństwo
        breakfast = random.random() < prob_breakfast

        prob_ios = 0.85 # niezależnie od dochodu snob prawie zawsze musi mięc iPhone
        device = "iOS" if random.random() < prob_ios else "Android"

        cities = ["Warszawa", "Kraków", "Poznań", "Wrocław", "Gdańsk", "Bytom"]
        if total_income > 20000:
            weights = [0.4, 0.18, 0.15, 0.15, 0.1, 0.02]
        else:
            weights = [0.3, 0.2, 0.15, 0.15, 0.15, 0.05]
        city = random.choices(cities, weights=weights, k=1)[0]

        # 4. Zmienne niezależne (Szum)
        get_up_with_left_foot = random.random() < 0.15
        returning_client = random.random() < 0.25

        self._context = {
            "city": city,
            "device": device,
            "returning_client": returning_client
        }

        self._public_data = {
            "current_date": current_date,
            "checkin": checkin.strftime("%Y-%m-%d"),
            "checkout": checkout.strftime("%Y-%m-%d"),
            "guests": guests,
            "room_type": room_type,
            "breakfast": breakfast,
            "context": self._context
        }

        self._hidden_data = {
            "days_to_vacation": days_to_vacation,
            "monthly_income_per_person": round(monthly_income_per_person, 2),
            "max_budget_per_person_per_day": round(budget_per_person_per_day, 2),
            "get_up_with_left_foot": get_up_with_left_foot,
            "is_vacation_time_strictly_locked": days_to_vacation < 30,
            "days_to_stay": days_to_stay
        }