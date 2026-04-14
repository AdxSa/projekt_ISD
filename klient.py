import requests
from person1_family_type import BasePerson_1, FamilyDataPool
import time
import random

request_url = "https://skydiver-filter-chivalry.ngrok-free.dev/receive"
answer_url = "https://skydiver-filter-chivalry.ngrok-free.dev/decision"


FamilyDataPool.get_data()  # generowanie próby w pamięci podręcznej
print("Rozpoczynam symulację napływających zapytań. Symulacja potrwa 60 sekund...\n")

start_time = time.time()
duration = 15  # czas w sekundach
request_count = 0

while time.time() - start_time < duration:
    # 1. Tworzymy nową instancję persony w każdej iteracji.
    current_person = BasePerson_1()

    # 2. Generujemy zapytanie (zakładamy statyczną datę lub możemy ją przesuwać)
    request = current_person.generate_requests('2026-02-11')
    request_count += 1

    # 3. Wypisujemy wynik na konsolę
    print(f"--- Zapytanie nr {request_count} ---")
    print(request)
    print("-" * 40)

    # 4. Usypiamy pętlę na losowy czas, np. od 0.5 do 3.5 sekundy,
    # aby zasymulować realistyczny ruch (zapytania nie wpadają co milisekundę)
    sleep_time = random.uniform(0.5, 3.5)
    time.sleep(sleep_time)

    r = requests.post(request_url, json=request)
    offers = [r.json()]
    answer = current_person.decide(offers)

    a = requests.post(answer_url, json=answer)

    print(offers)
    print(a.json())

print(f"\nKoniec symulacji. W ciągu minuty wygenerowano {request_count} unikalnych zapytań od klientów rodzinnych.")


# Output:
