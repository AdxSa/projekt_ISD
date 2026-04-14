import os
import random
import numpy as np
import pandas as pd
from scipy.stats import norm, poisson
from datetime import datetime, timedelta
from dynamic_copula import generate_dynamic_copula_data


class BusinessDataPool:
    _data = None
    _FILE_PATH = "business_base_profiles.csv"

    @classmethod
    def get_data(cls, data_size=10000):
        if cls._data is not None and data_size != 1:
            return cls._data

        if os.path.exists(cls._FILE_PATH):
            print(f"Wczytywanie puli profili biznesowych z pliku: {cls._FILE_PATH}...")
            cls._data = pd.read_csv(cls._FILE_PATH)
        else:
            print("Plik nie istnieje. Generowanie nowej puli profili biznesowych...")

            target_matrix = np.array([
                [1.0, -0.2,  0.1,  0.35, 0.15],
                [-0.2, 1.0,  0.2, -0.1,  0.1],
                [0.1,  0.2,  1.0,  0.1,  0.1],
                [0.35, -0.1, 0.1,  1.0,  0.25],
                [0.15, 0.1,  0.1,  0.25, 1.0]
            ])

            ppfs = [
                lambda u: norm(loc=14000, scale=4500).ppf(u),   # income
                lambda u: poisson(mu=5).ppf(u) + 1,             # days_to_trip
                lambda u: poisson(mu=1.5).ppf(u) + 1,           # days_to_stay
                lambda u: norm(loc=0, scale=1).ppf(u),          # comfort_level
                lambda u: norm(loc=0, scale=1).ppf(u),          # breakfast_affinity
            ]

            cls._data = generate_dynamic_copula_data(
                target_matrix,
                ppfs,
                ["income", "days_to_trip", "days_to_stay", "comfort_level", "breakfast_affinity"],
                num_samples=data_size
            )

            cls._data["income"] = cls._data["income"].clip(lower=5000)
            cls._data["days_to_trip"] = cls._data["days_to_trip"].clip(lower=1, upper=60)
            cls._data["days_to_stay"] = cls._data["days_to_stay"].clip(lower=1, upper=5)
            cls._data["comfort_level"] = cls._data["comfort_level"].clip(-2.5, 2.5)
            cls._data["breakfast_affinity"] = cls._data["breakfast_affinity"].clip(-2.5, 2.5)

            cls._data.to_csv(cls._FILE_PATH, index=False)
            print(f"Zapisano nową pulę profili biznesowych do pliku: {cls._FILE_PATH}")

        return cls._data

    @classmethod
    def sample_base_profile(cls):
        return cls.get_data().sample(1).iloc[0].to_dict()


class BasePerson_Business:
    def __init__(self):
        self.name = "Biznesowy"
        self.description = (
            "Klient biznesowy podróżujący zwykle solo, na krótki pobyt, "
            "wybierający termin, typ pokoju i śniadanie."
        )
        self.base_profile = None
        self._public_data = None
        self._hidden_data = None
        self._context = None

    def generate_requests(self, current_date: str) -> dict:
        if self._public_data:
            return self._public_data
        self._get_info(current_date)
        return self._public_data

    def decide(self, offers: list[dict]) -> dict:
        """
        Oczekiwany format oferty:
        {
            "offer_id": "a1b2c3",
            "price": 550.0,                    # cena całkowita za cały pobyt
            "room_type": "standard_single",   # standard_single / standard_double / deluxe_double
            "breakfast_included": True,
            "valid_seconds": 30
        }
        """

        if self._public_data is None or self._hidden_data is None or self._context is None:
            raise RuntimeError("Najpierw wywołaj generate_requests(current_date).")

        if not offers:
            return {
                "offer_id": None,
                "decision": "decline",
                "chosen_option": "decline",
                "probabilities": {"decline": 1.0},
                "utilities": {"decline": 0.0}
            }

        days = self._hidden_data["days_to_stay"]
        max_budget_per_night = self._hidden_data["max_budget_per_night"]
        payer_type = self._hidden_data["payer_type"]
        preferred_room_type = self._hidden_data["preferred_room_type"]
        room_upgrade_tolerance = self._hidden_data["room_upgrade_tolerance"]
        breakfast_preference_strength = self._hidden_data["breakfast_preference_strength"]
        days_to_trip = self._hidden_data["days_to_trip"]

        returning_client = self._context["returning_client"]
        wants_breakfast = self._public_data["breakfast"]

        utilities = {}

        # --------------------------------------------------
        # OUTSIDE OPTION: "decline"
        # --------------------------------------------------
        # Bazowa skłonność do odrzucenia:
        # - maleje dla returning_client
        # - maleje, gdy wyjazd jest blisko
        V0 = 0.3
        if returning_client:
            V0 -= 0.35
        V0 -= 0.8 * np.exp(-0.25 * days_to_trip)

        utilities["decline"] = V0

        # --------------------------------------------------
        # Utility ofert
        # --------------------------------------------------
        for offer in offers:
            offer_id = offer.get("offer_id")
            total_price = float(offer.get("price", 1000.0))
            room_type = offer.get("room_type", "standard_single")
            breakfast_included = bool(offer.get("breakfast_included", False))

            price_per_night = total_price / max(days, 1)
            price_ratio = price_per_night / max(max_budget_per_night, 1e-9)

            V = 0.0

            # 1. Bonus dla powracającego klienta
            if returning_client:
                V += 0.4

            # 2. Cena zależna od payer_type
            if payer_type == "self_paid":
                V += 0.6 * max(0.0, 1 - price_ratio)
                V -= 2.4 * max(0.0, price_ratio - 1)

            elif payer_type == "reimbursed_with_cap":
                V += 0.4 * max(0.0, 1 - price_ratio)
                V -= 1.8 * max(0.0, price_ratio - 1)

            elif payer_type == "corporate":
                V += 0.25 * max(0.0, 1 - price_ratio)
                V -= 1.1 * max(0.0, price_ratio - 1)

            # 3. Dopasowanie typu pokoju
            V += self._room_utility(
                offered_room_type=room_type,
                preferred_room_type=preferred_room_type,
                room_upgrade_tolerance=room_upgrade_tolerance,
                payer_type=payer_type
            )

            # 4. Śniadanie
            if wants_breakfast and breakfast_included:
                V += breakfast_preference_strength
            elif wants_breakfast and not breakfast_included:
                V -= 0.9 * breakfast_preference_strength
            elif (not wants_breakfast) and breakfast_included:
                V -= 0.1

            # 5. Urgency
            # Im bliżej wyjazdu, tym większa skłonność do zaakceptowania sensownej oferty.
            V += 1.2 * np.exp(-0.25 * days_to_trip)

            utilities[offer_id] = V

        # --------------------------------------------------
        # MULTINOMIAL LOGIT / SOFTMAX
        # --------------------------------------------------
        option_names = list(utilities.keys())
        V_array = np.array([utilities[name] for name in option_names], dtype=float)

        # stabilizacja numeryczna
        V_max = np.max(V_array)
        exp_V = np.exp(V_array - V_max)
        probs = exp_V / exp_V.sum()

        probability_dict = {
            option_names[i]: float(probs[i]) for i in range(len(option_names))
        }

        # losowanie jednej opcji z rozkładu kategorycznego
        chosen_idx = np.random.choice(len(option_names), p=probs)
        chosen_option = option_names[chosen_idx]

        if chosen_option == "decline":
            return {
                "offer_id": None,
                "decision": "decline",
                "chosen_option": chosen_option,
                "probabilities": probability_dict,
                "utilities": utilities
            }

        return {
            "offer_id": chosen_option,
            "decision": "accept",
            "chosen_option": chosen_option,
            "probabilities": probability_dict,
            "utilities": utilities
        }

    def _room_utility(
        self,
        offered_room_type: str,
        preferred_room_type: str,
        room_upgrade_tolerance: float,
        payer_type: str
    ) -> float:
        """
        Utility z dopasowania typu pokoju.
        Typy:
        - standard_single
        - standard_double
        - deluxe_double
        """

        if offered_room_type == preferred_room_type:
            return 0.7

        if preferred_room_type == "standard_single":
            if offered_room_type == "standard_double":
                return 0.15
            elif offered_room_type == "deluxe_double":
                return -0.35 + 0.4 * room_upgrade_tolerance

        if preferred_room_type == "standard_double":
            if offered_room_type == "standard_single":
                return -0.6
            elif offered_room_type == "deluxe_double":
                return 0.25 + 0.35 * room_upgrade_tolerance

            #### (moze) uzaleznic room_upgrade_tolarance od typu klienta
            #### (moze) dodac analogicznie room_downgrade_tolerance client's type dependent

        if preferred_room_type == "deluxe_double":
            if offered_room_type == "standard_single":
                return -0.9
            elif offered_room_type == "standard_double":
                return -0.25

        return 0.0

    def _get_info(self, current_date: str) -> None:
        current_date_dt = datetime.strptime(current_date, "%Y-%m-%d")

        self.base_profile = BusinessDataPool.sample_base_profile()

        income = float(self.base_profile["income"])
        days_to_trip = int(self.base_profile["days_to_trip"])
        days_to_stay = int(self.base_profile["days_to_stay"])
        comfort_level = float(self.base_profile["comfort_level"])
        breakfast_affinity = float(self.base_profile["breakfast_affinity"])

        checkin = current_date_dt + timedelta(days=days_to_trip)
        checkout = checkin + timedelta(days=days_to_stay)

        returning_client = random.random() < 0.22
        device = "iOS" if income > 15000 and random.random() < 0.7 else "Android"

        self._context = {
            "device": device,
            "returning_client": returning_client
        }

        u = random.random()
        if income < 10000:
            payer_type = "self_paid" if u < 0.55 else "reimbursed_with_cap"
        elif income < 18000:
            if u < 0.20:
                payer_type = "self_paid"
            elif u < 0.75:
                payer_type = "reimbursed_with_cap"
            else:
                payer_type = "corporate"
        else:
            if u < 0.10:
                payer_type = "self_paid"
            elif u < 0.45:
                payer_type = "reimbursed_with_cap"
            else:
                payer_type = "corporate"

        guests = 1 if random.random() < 0.9 else 2

        if guests == 2:
            if comfort_level > 0.8:
                preferred_room_type = "deluxe_double"
            else:
                preferred_room_type = "standard_double"
        else:
            if comfort_level < -0.3:
                preferred_room_type = "standard_single"
            elif comfort_level < 0.9:
                preferred_room_type = random.choices(
                    ["standard_single", "standard_double"],
                    weights=[0.7, 0.3],
                    k=1
                )[0]
            else:
                preferred_room_type = random.choices(
                    ["standard_double", "deluxe_double"],
                    weights=[0.55, 0.45],
                    k=1
                )[0]

        room_upgrade_tolerance = float(np.clip(0.8 + 0.35 * comfort_level, 0.0, 1.8))

        breakfast_prob = 0.55 + 0.12 * breakfast_affinity
        breakfast_prob = float(np.clip(breakfast_prob, 0.2, 0.9))
        breakfast = random.random() < breakfast_prob

        breakfast_preference_strength = float(np.clip(0.35 + 0.25 * breakfast_affinity, 0.1, 1.0))

        if payer_type == "self_paid":
            max_budget_per_night = 0.07 * income
        elif payer_type == "reimbursed_with_cap":
            max_budget_per_night = 0.09 * income
        else:  # corporate
            max_budget_per_night = 0.11 * income + 30 * max(comfort_level, 0)

        max_budget_per_night = float(round(max(180, max_budget_per_night), 2))

        self._public_data = {
            "current_date": current_date,
            "checkin": checkin.strftime("%Y-%m-%d"),
            "checkout": checkout.strftime("%Y-%m-%d"),
            "guests": guests,
            "breakfast": breakfast,
            "context": self._context
        }

        self._hidden_data = {
            "days_to_trip": days_to_trip,
            "days_to_stay": days_to_stay,
            "max_budget_per_night": max_budget_per_night,
            "payer_type": payer_type,
            "preferred_room_type": preferred_room_type,
            "room_upgrade_tolerance": room_upgrade_tolerance,
            "breakfast_preference_strength": round(breakfast_preference_strength, 3),
        }