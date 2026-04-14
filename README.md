## Persona: Family Client

### Opis ogólny
Klient typu **Family** to osoba planująca wyjazd rodzinny (3+ osób), zazwyczaj z dużym wyprzedzeniem. Charakteryzuje się większą wrażliwością cenową oraz koniecznością dopasowania oferty do potrzeb całej rodziny (dzieci, długość pobytu, terminy szkolne).

---

### Profil finansowy
- Dochód na dorosłego: ~ N(8000, 2500)
- Zakładamy 2 pracujących dorosłych:
  total_income ≈ 2 × income
- Budżet na wyjazd:
  ~ 40% całkowitego dochodu
- Wysoka wrażliwość na cenę (szczególnie przy większej liczbie gości)

---

### Preferencje pobytowe
- Liczba gości: 3–7 osób
- Długość pobytu:
  ~ Poisson(5) + 2  (czyli głównie 4–8 dni)
- Preferencja dla pokoi rodzinnych:
  np. [2+2], [3+2], [2+2+2]
- Śniadanie:
  im większy budżet → tym większa szansa wyboru

---

### Zachowanie rezerwacyjne
- Rezerwacje z dużym wyprzedzeniem:
  days_to_vacation ~ N(75, 20)
- Często termin jest „sztywny” (urlop zatwierdzony, szkoła dzieci)
- Mniejsza elastyczność niż u klientów indywidualnych

---

### Model decyzyjny
Prawdopodobieństwo akceptacji:

P(accept) = 1 / (1 + exp(-U))

gdzie U to funkcja użyteczności.

---

### Czynniki zwiększające U
- Cena poniżej budżetu
- Status klienta powracającego
- Krótki czas do wyjazdu (efekt presji)
- Początek pobytu w weekend (łatwiejsza organizacja dla dzieci)

---

### Czynniki zmniejszające U
- Cena powyżej budżetu
- Duża liczba gości (większa wrażliwość cenowa)
- Pobyt zaczynający się w środku tygodnia (problemy logistyczne)
- „Zły humor” (losowy czynnik)

---

### Wpływ terminu (bardzo ważne)
Dla krótkich pobytów (≤ 4 dni):
- weekend start → pozytywny efekt
- środek tygodnia → negatywny efekt

Dla długich pobytów:
- weekend → lekki bonus
- środek tygodnia → neutralny

---

### Kontekst
- Miasto wybierane losowo:
  Warszawa, Kraków, Wrocław, Gdańsk, Poznań, Bytom
- Urządzenie:
  iOS częściej przy wyższych dochodach

---

### Element losowy
Model zawiera komponent losowy:
- 5% szans na „zły humor”
- 15% szans na klienta powracającego
- zmienność zachowań między rodzinami

---

### Cel modelu
Persona „Family” służy do:
- symulacji klientów masowych (segment leisure)
- testowania strategii cenowych przy dużej liczbie gości
- analizy wpływu ceny i terminu na decyzje rodzin

---

## Persona: Snob Client

### Opis ogólny
Klient typu **Snob** to zamożna, wymagająca osoba podróżująca samotnie lub z partnerem. Charakteryzuje się wysokimi oczekiwaniami oraz dużą wrażliwością na jakość i prestiż oferty. Często dokonuje rezerwacji w trybie *last-minute* i preferuje krótkie pobyty o wysokim standardzie.

---

### Profil finansowy
- Dochód: ~ N(15000, 4000)
- Budżet na wyjazd: ~ 60% dochodu
- Preferencja dla ofert w „premium sweet spot” (ani za tanie, ani za drogie)

---

### Preferencje pobytowe
- Liczba gości: 1–2 osoby
- Długość pobytu: ~ Poisson(2) + 1 (czyli głównie 1–3 dni)
- Częsty wybór pokoi typu **suite**, zwłaszcza podróżując z partnerem (chęć zaimponowania)
- Wysoka skłonność do wyboru śniadania
- Preferencja dla urządzeń iOS

---

### Zachowanie rezerwacyjne
- Często rezerwuje:
  - last-minute: ~ N(7, 3)
  - planowane: ~ N(30, 10)
- Im mniej czasu do wyjazdu → tym większa szansa akceptacji oferty (*urgency effect*)
- Klienci powracający mają wyższą skłonność do zakupu

---

### Model decyzyjny

Prawdopodobieństwo akceptacji:

P(accept) = 1 / (1 + exp(-U))

gdzie U to funkcja użyteczności.

---

### Czynniki zwiększające U
- Cena w optymalnym zakresie:
  0.7 ≤ price / budget ≤ 1.3
- Status klienta powracającego
- Wysoka pilność (mało dni do wyjazdu)
- Pobyt bez weekendu (cisza, brak tłumów)

---

### Czynniki zmniejszające U
- Zbyt niska cena (podejrzenie niskiej jakości)
- Zbyt wysoka cena
- Pobyt obejmujący weekend (tłumy, dużo dzieci - wpływają negatywnie)
- „Zły humor” (losowy czynnik)

---

### Kontekst geograficzny
Miasto wybierane jest losowo z wagami zależnymi od dochodu.

Najczęstsze wybory:
- Warszawa
- Kraków
- Wrocław
- Gdańsk

Rzadziej:
- Poznań
- Bytom

---

### Element losowy
Model uwzględnia:
- zmienność nastroju
- nieprzewidywalność decyzji
- różnorodność klientów

---
