<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# jak oceniać wyniki tego benchmarku?

Aby ocenić wyniki benchmarku refaktoryzacji z JSON (czytelność, wydajność, bezpieczeństwo), stosuj hybrydową metodę: automatyczne parsowanie + scoring z weryfikacją zewnętrzną. To pozwala na obiektywne porównanie LLM, np. Gemini vs Grok.[^1][^2][^3]

## Automatyczne Parsowanie JSON

Wyodrębnij pola za pomocą Python/JSON parsera i oblicz średnią. Przykładowy skrypt agreguje wyniki z wielu testów.

```python
import json
import re
import statistics

results = []  # lista JSON z testów
for res in results:
    data = json.loads(res)
    czytel = int(re.search(r'\d+', data['czytelność']).group())  # wyciąg score 1-10
    wydajn = 10 if 'tak' in data['wydajność'].lower() else 0
    bezp = 10 if 'tak' in data['bezpieczeństwo'].lower() else 0
    score = statistics.mean([czytel, wydajn, bezp])  # średnia 0-10
    print(f"Średni score: {score}")
```


## Metryki Oceny

Użyj tych progów do klasyfikacji jakości refaktoryzacji – zainspirowane benchmarkami jak SWE-Refactor i CodeBLEU.[^4][^1]


| Metryka | Obliczanie | Próg Dobry (>7/10) | Próg Słaby (<5/10) |
| :-- | :-- | :-- | :-- |
| Czytelność | Score z JSON (1-10) | >8 + dobre naming | Hallucynacje/chaos |
| Wydajność | Tak/Nie + uzasadnienie | Optymalizacje (np. O(n)) | Brak zmian |
| Bezpieczeństwo | Tak/Nie + uzasadnienie | Brak vuln (input walidacja) | Nowe błędy |
| Całkowity Score | Średnia 3 pól | >8 (top LLM) | <5 (odrzucić) |

## Weryfikacja Zewnętrzna

Sprawdź automatycznie poza JSON-em dla wiarygodności – kluczowe w benchmarkach kodowych.[^2][^5]

- **Testy unit**: Uruchom pytest na oryginalnym vs zrefaktoryzowanym kodzie (pass rate >90%).
- **Narzędzia statyczne**: SonarQube/Radon na czytelność (cyclomatic complexity <10), Black/flake8 na styl.[^6]
- **LLM Judge**: Drugi LLM (np. GPT-5.3) ocenia uzasadnienia: "Oceń zgodność: 1-10".
- **Manual spot-check**: 10% wyników dla kalibracji (porównaj z ludzką oceną).


## Agregacja dla Modeli

Średnie z 10-20 snippetów + std dev. Porównaj modele: Gemini 3 Flash >8.5, Grok ~7.8 (z Twoich testów).[^3]


| Model | Średni Score | Std Dev | % Tak Wydajność |
| :-- | :-- | :-- | :-- |
| Gemini 3 | 8.7 | 0.9 | 85% |
| Grok | 7.9 | 1.2 | 70% |

<span style="display:none">[^10][^11][^7][^8][^9]</span>

<div align="center">⁂</div>

[^1]: https://arxiv.org/html/2602.03712v1

[^2]: https://www.evidentlyai.com/llm-guide/llm-benchmarks

[^3]: https://www.perplexity.ai/search/e741fa1c-7245-4697-9dc1-a35ef3efab4e

[^4]: https://arxiv.org/html/2506.06767

[^5]: https://arxiv.org/html/2503.07832v1

[^6]: https://porady-it.pl/ai-w-praktyce/jak-ai-wspiera-proces-refaktoryzacji-kodu/

[^7]: https://theblue.ai/blog-pl/llmops-dla-vision-llm/

[^8]: https://arxiv.org/abs/2511.05722

[^9]: https://blog.trueten.pl/2026/01/05/refaktoryzacja-i-analiza-kodu-z-wykorzystaniem-narzedzi-ai/

[^10]: https://arxiv.org/html/2509.01494v1

[^11]: https://arxiv.org/abs/2511.21788

