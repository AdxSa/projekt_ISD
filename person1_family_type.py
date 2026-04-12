
import os
import numpy as np
import pandas as pd
from scipy.stats import norm, randint, poisson, bernoulli
from datetime import datetime, timedelta
from dynamic_copula import generate_dynamic_copula_data
import random
import time
import math


class FamilyDataPool:
    _data = None
    _FILE_PATH = "family_base_profiles.csv"

    @classmethod
    def get_data(cls, data_size = 10000):
        # Jeśli dane są w pamięci podręcznej, zwróć
        if cls._data is not None and data_size != 1:
            return cls._data

        # Sprawdź, czy wygenerowane trajektorie lub wygenerować nowe trajektorie
        if os.path.exists(cls._FILE_PATH):
            print(f"Wczytywanie puli profili z pliku: {cls._FILE_PATH}...")
            cls._data = pd.read_csv(cls._FILE_PATH)
        else:
            print("Plik nie istnieje. Generowanie nowej puli profili (Copula)...")
            
            # Definicja rozkładów - specyficzne dla każdej persony

            ## definiujemy macierz korelacji
            target_matrix = np.array([
                [1.0, -0.1,  0.2,  0.1], 
                [-0.1, 1.0, -0.3,  0.5], 
                [ 0.2,-0.3,  1.0,  0.6], 
                [ 0.1, 0.5,  0.6,  1.0]  
            ])

            ## definiujemy docelowe rozkłady za pomocą ppf
            ppfs = [
                lambda u: norm(loc=8000, scale=2500).ppf(u), # średni dochód na osobę dorosłą
                lambda u: randint(low=3, high=8).ppf(u),     # ilość członków rodziny
                lambda u: poisson(mu=5).ppf(u) + 2,          # liczba dni postoju
                lambda u: norm(loc=75, scale=20).ppf(u)      # liczba dni do urlopu
            ]

            ## generowanie zadanych rozkładów za pomocą funkcji copula
            cls._data = generate_dynamic_copula_data(
                target_matrix, ppfs, 
                ["income", "guests", "days_to_stay", "days_to_vacation"], 
                num_samples=data_size
            )
            
            cls._data['income'] = cls._data['income'].clip(lower=3000) ## zakładamy pensję minimalną jako dolny cap
            cls._data['days_to_vacation'] = cls._data['days_to_vacation'].clip(lower=1) 
            
            # ZAPIS DO PLIKU: w przyszłych uruchomieniach pobieramy pojedynczą wartość
            cls._data.to_csv(cls._FILE_PATH, index=False)
            print(f"Zapisano nową pulę profili do pliku: {cls._FILE_PATH}")
            
        return cls._data

    @classmethod
    def sample_base_profile(cls):
        """zwraca losowy, zapisany wiersz z wygenerowanej wcześniej próby"""
        return cls.get_data().sample(1).iloc[0].to_dict()


class BasePerson_1:
    def __init__(self):
        self.name = 'Rodzinny'
        self.description = "Klient szukający wypoczynku dla 3+ osób, planujący z wyprzedzeniem."
        self.base_profile = None # Zostanie wypełnione przy generowaniu zapytania
        self._public_data = None  

    def generate_requests(self, current_date: str) -> dict:
        if self._public_data:
            return self._public_data
        else:
            self._get_info(current_date)
            return self._public_data
        
    def decide(self, offers: list[dict]) -> str | None:
        
        # offer = {
        # "offer_id" : "a1b2c3",
        # "price": 750.00,
        # "valid_seconds" : 30}
        
        # logika akceptacji oferty

        if not offers:
            return {
                "offer_id": None,
                "decision": "decline"
            }
        """
        Podejmuje decyzję na podstawie otrzymanej oferty i cech klienta.
        """
        guests = self._public_data["guests"]
        days = int(self.base_profile['days_to_stay'])
        days_to_vacation = self.base_profile['days_to_vacation']
        returning_client = self._context["returning_client"]

        max_budget_per_person_per_day = self._hidden_data["max_budget_per_person_per_day"]
        get_up_with_left_foot = self._hidden_data["get_up_with_left_foot"]
        is_vacation_time_strictly_locked = self._hidden_data["is_vacation_time_strictly_locked"]
        

        offers_utility = {}
        for offer in offers:
            offered_total_price = offer.get("price", 1000)
            price_per_person_per_day = offered_total_price / (guests * days)
            


            # Różnica cenowa: dodatnia = oszczędność, ujemna = przekroczenie budżetu
            price_diff = max_budget_per_person_per_day - price_per_person_per_day
            price_ratio = price_per_person_per_day / max_budget_per_person_per_day
            
            # (Kalibracja psychologii klienta)
            # Kalibracja wag w funkcji użyteczności U i kalkulacja funkcji
            # Dokładne wartości do przemyślenia::

            if get_up_with_left_foot and price_diff < 0:
                U = -1000
            else: U = 0

            ## Bazowa skłonność do rezerwacji
            if returning_client:
                w_base = 0.5  
            else:    w_base = 0 
            U += w_base

            ## Wrażliwość cenowa, w zależności od proporcji price/budget
            ## skalowalne od ilości gości, więcej gości - większa wrażliwość
            w_price = guests * 0.75
            U +=  w_price * (1 - price_ratio) 


            ## Brak czasu na zmianę planów mocno podbija użyteczność
            
            if is_vacation_time_strictly_locked:
                max_urgency = 2.5   # Maksymalny bonus, gdy rezerwujemy "na jutro"
                decay_rate = 0.05   # Jak szybko panika spada. (Przy 0.07 panika zaczyna się ok. 3 tygodnie przed wyjazdem.)
                w_urgency = max_urgency * np.exp(-decay_rate * days_to_vacation)
                U +=  w_urgency
            else:
                max_urgency = 2.5   # Maksymalny bonus, gdy rezerwujemy "na jutro"
                decay_rate = 0.13   # Jak szybko panika spada. (Przy 0.07 panika zaczyna się ok. 3 tygodnie przed wyjazdem.)
                w_urgency = max_urgency * np.exp(-decay_rate * days_to_vacation)
                U +=  w_urgency


            ## wrażliwość weekendowa

            checkin_date = datetime.strptime(self._public_data["checkin"], "%Y-%m-%d")
            day_of_week = checkin_date.weekday() # 0 = Poniedziałek, 4 = Piątek, 5 = Sobota, 6 = Niedziela
            weekend_bonus = 0.0
            is_weekend_start = day_of_week in [4, 5] # Zaczynamy w piątek lub sobotę

            if days <= 4:
                # KRÓTKI WYJAZD
                if is_weekend_start:
                    weekend_bonus = 0.5 # Rodzina przymknie oko na zawyżoną cenę, aby nie zwalniać dzieci ze szkoły i nie brać nadmiarowego urlopu.
                else:
                    weekend_bonus = -0.5 # Środek tygodnia -- problem
            else:
                # DŁUGI WYJAZD
                if is_weekend_start or day_of_week == 6:
                    weekend_bonus = 0.2  # Miły dodatek
                else:
                    weekend_bonus = 0.0  # Środek tygodnia jest neutralny
            U += weekend_bonus

            
            offers_utility[offer.get("offer_id")] = U


        # Funkcja logistyczna  U --> prawdopodobieństwo akceptacji
        Best_offer = max(offers_utility.items(), key = lambda x : x[1])
        try:
            p_accept = 1 / (1 + math.exp(-Best_offer[1]))
        except OverflowError:
            p_accept = 0.0 # fallback
            
        if random.random() < p_accept:
            return {
                "offer_id" : Best_offer[0],
                "decision" : "accept"
            }
        else:
            return {
                "offer_id" : None,
                "decision" : "decline"
            }

    def _determine_rooms(self, guests: int) -> list[int]:
        """Rozbija ilość gości na konkretne pokoje."""
        if guests == 3: return random.choice([[3], [2, 1]])
        if guests == 4: return random.choice([[4], [2, 2]])
        if guests == 5: return random.choice([[3, 2], [5]])
        if guests == 6: return random.choice([[3, 3], [2, 2, 2]])
        if guests == 7: return [3, 2, 2]
        return [guests] # fallback

    def _get_info(self, current_date: str) -> tuple[dict, dict, dict]:
        """
        Zwraca krotkę (public_data, hidden_data, context)
        """
        current_date_date = datetime.strptime(current_date, "%Y-%m-%d")

        # 1. Pobierz bazowe zmienne skorelowane z puli.
        self.base_profile = FamilyDataPool.sample_base_profile()
        
        guests = int(self.base_profile['guests'])
        days_to_stay = int(self.base_profile['days_to_stay'])
        days_to_vacation = int(self.base_profile['days_to_vacation'])
        total_adult_income = self.base_profile['income']

        # 2. Oblicz Daty
        checkin = current_date_date + timedelta(days=days_to_vacation)
        checkout = checkin + timedelta(days=days_to_stay)

        # 3. Zmienne pochodne (logika biznesowa)
        
        # Dochód na osobę = dochód rodziny (na razie zakładamy 2 pracujących) / ilość gości
        # trzeba dodać premie +800 plus na każde dziecko
        monthly_income_per_person = (total_adult_income * 2) / guests
        
        # Budżet na cały wyjazd (na razie 40% miesięcznego dochodu na wyjazd)
        total_trip_budget = (total_adult_income * 2) * 0.40 
        budget_per_person_per_day = total_trip_budget / (guests * days_to_stay)
        # print(budget_per_person_per_day)

        # Śniadanie - im większy budżet na osobę na dzień, tym chętniej biorą śniadanie
        prob_breakfast = min(0.9, max(0.2, (budget_per_person_per_day / 300))) # Skalujemy prawdopodobieństwo
        breakfast = random.random() < prob_breakfast

        # Context - do przemyślenia 
        ## Urządzenie - bogatsi częściej mają iOS, na razie prosta logika - może dobrze
        prob_ios = 0.7 if monthly_income_per_person > 5000 else 0.3
        device = "iOS" if random.random() < prob_ios else "Android"

        ## Miasto - na teraz losowe z listy dużych miast, docelowo skorelowane z income i ilością dzieci
        city = random.choice(["Warszawa", "Kraków", "Poznań", "Wrocław", "Gdańsk", "Bytom"])

        # 4. Zmienne niezależne (Szum)
        get_up_with_left_foot = random.random() < 0.05 # 5% szans że wstał lewą nogą --> zwiększa marudność na cenę ponad budget
        returning_client = random.random() < 0.15 # 15% szans że to stały klient, duży wpływ że to klient rodzinny


        # Składanie wyników:
        

        self._context = {
            "city": city,
            "device": device,
            "returning_client": returning_client
        }

        self._public_data = {
            "current_date" : current_date,
            "checkin": checkin.strftime("%Y-%m-%d"),
            "checkout": checkout.strftime("%Y-%m-%d"),
            "guests": guests,
            "room_types": self._determine_rooms(guests), ## tutaj zmiana względem wymagań projektowych, dopytać
            "breakfast": breakfast,
            "context": self._context
        }

        self._hidden_data = {
            "days_to_vacation": days_to_vacation,
            "monthly_income_per_person": round(monthly_income_per_person, 2),
            "max_budget_per_person_per_day": round(budget_per_person_per_day, 2),
            "get_up_with_left_foot": get_up_with_left_foot,
            "is_vacation_time_strictly_locked": days_to_vacation < 30, # Jeśli mało czasu, urlop przyklepany w HR
            "days_to_stay": days_to_stay
        }




# # ==========================================
# # SYMULACJA RUCHU ## test generatora zapytań
# # ==========================================
# FamilyDataPool.get_data() # generowanie próby w pamięci podręcznej
# print("Rozpoczynam symulację napływających zapytań. Symulacja potrwa 60 sekund...\n")
#
# start_time = time.time()
# duration = 60 # czas w sekundach
# request_count = 0
#
# while time.time() - start_time < duration:
#     # 1. Tworzymy nową instancję persony w każdej iteracji.
#     current_person = BasePerson_1()
#
#     # 2. Generujemy zapytanie (zakładamy statyczną datę lub możemy ją przesuwać)
#     request = current_person.generate_requests('2026-02-11')
#     request_count += 1
#
#     # 3. Wypisujemy wynik na konsolę
#     print(f"--- Zapytanie nr {request_count} ---")
#     print(request)
#     print("-" * 40)
#
#     # 4. Usypiamy pętlę na losowy czas, np. od 0.5 do 3.5 sekundy,
#     # aby zasymulować realistyczny ruch (zapytania nie wpadają co milisekundę)
#     sleep_time = random.uniform(0.5, 3.5)
#     time.sleep(sleep_time)

# print(f"\nKoniec symulacji. W ciągu minuty wygenerowano {request_count} unikalnych zapytań od klientów rodzinnych.")