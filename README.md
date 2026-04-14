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
