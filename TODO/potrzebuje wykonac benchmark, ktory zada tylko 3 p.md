<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# potrzebuje wykonac benchmark, ktory zada tylko 3 pytania, na ktore trzeba bedzie odpowiedziec w jednym json ze strony LLM

chcialbm aby odpowieddzi na te pytania pokazaly jakosc refaktoryzacji, ale aby dane wesjciowe nie zajmowaly wiecej niz 500Bjaktow danych, jaki to pwinien byc prompt?

Oto przykładowy prompt do benchmarku refaktoryzacji, który zadaje dokładnie 3 pytania oceniające jakość, wymusza pojedynczy JSON jako odpowiedź i mieści się z przykładowym kodem wejściowym poniżej 500 bajtów (cały prompt + kod ~380B). Prompt skupia się na kluczowych aspektach refaktoryzacji: czytelności, wydajności i bezpieczeństwie, co pokazuje jakość pracy LLM.[^1][^2][^3]

## Struktura Promptu

```
Analizuj refaktoryzację poniższego kodu. Odpowiedz TYLKO jednym valid JSON: {"czytelność": "score 1-10 + uzasadnienie", "wydajność": "czy poprawiona? uzasadnienie", "bezpieczeństwo": "czy poprawione? uzasadnienie"}. Nie dodawaj tekstu poza JSON.

KOD WEJŚCIOWY:
def sum_list(lst): return sum(lst) # przykład do refaktoryzacji

TWOJA REF AKTORYZACJA:
[tu wklej wynik LLM]
```


## Dlaczego Ten Prompt Działa

- **3 precyzyjne pytania**: Ocena czytelności (czytelność kodu), poprawy wydajności (optymalizacje) i bezpieczeństwa (unikanie błędów/wułnerności) – standardowe metryki refaktoryzacji.[^3][^4]
- **Jedyny JSON**: Wymusza strukturalny output bez markdownu czy wyjaśnień, co ułatwia parsowanie (inspirowane technikami z prompt engineering).[^5][^6]
- **Limit <500B**: Bazowy prompt ~250B, kod wejściowy <100B (krótki przykład), refaktoryzacja <150B – skalowalny dla małych snippetów jak funkcje Python/embedded.[^7]
- **Miara jakości**: Score + uzasadnienie pozwala na automatyczną ocenę (np. avg score >8 = dobra refaktoryzacja).[^8]


## Przykład Użycia

Dla kodu `def process(data): return [x*2 for x in data if x>0]`, po refaktoryzacji LLM prompt wygeneruje:
`{"czytelność": "9 - jasne nazwy, czytelna logika", "wydajność": "tak - unika list comp dla dużych danych", "bezpieczeństwo": "nie - brak walidacji input"}` – benchmark gotowy do agregacji.[^9]
<span style="display:none">[^10][^11][^12][^13][^14][^15][^16][^17][^18][^19][^20][^21][^22]</span>

<div align="center">⁂</div>

[^1]: https://www.perplexity.ai/search/e741fa1c-7245-4697-9dc1-a35ef3efab4e

[^2]: https://arxiv.org/abs/2511.21788

[^3]: https://www.arxiv.org/abs/2602.03712

[^4]: https://arxiv.org/html/2602.03712v1

[^5]: https://www.c-sharpcorner.com/article/get-structured-json-output-from-a-prompt/

[^6]: https://www.promptfoo.dev/docs/guides/evaluate-json/

[^7]: https://www.perplexity.ai/search/2b5a70cc-9029-4167-991f-39ac423ce88e

[^8]: https://www.perplexity.ai/search/0b45eaff-9b5f-4c4c-9b06-2ac5663744a8

[^9]: https://addyo.substack.com/p/the-prompt-engineering-playbook-for

[^10]: https://community.openai.com/t/prompt-engineering-showcase-your-best-practical-llm-prompting-hacks/1267113?page=2

[^11]: https://www.reddit.com/r/ChatGPTCoding/comments/1e4k5yk/an_ai_tool_to_check_the_quality_of_5000_lines_of/

[^12]: https://arxiv.org/html/2408.11061v1

[^13]: https://www.braintrust.dev/articles/best-prompt-evaluation-tools-2025

[^14]: https://dev.to/superorange0707/stop-parsing-nightmares-prompting-llms-to-return-clean-parseable-json-290o

[^15]: https://arxiv.org/pdf/2602.03712v1.pdf

[^16]: https://huggingface.co/papers/2509.10436

[^17]: https://understandlegacycode.com/blog/can-ai-refactor-legacy-code/

[^18]: https://aider.chat/2024/08/14/code-in-json.html

[^19]: https://arxiv.org/html/2508.14727v1

[^20]: https://openreview.net/forum?id=caPQXR9eeJ

[^21]: https://www.promptfoo.dev/docs/guides/evaluate-coding-agents/

[^22]: https://learn.microsoft.com/en-us/samples/dotnet/ai-samples/evaluate-llm-output/

