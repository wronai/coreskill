import { useState } from "react";

const sections = [
  { id: "platforms", label: "🖥️ Platformy" },
  { id: "apis", label: "🔌 3 API" },
  { id: "usecases", label: "🎯 Use Cases" },
  { id: "messaging", label: "💬 Jak mówić" },
  { id: "sales", label: "💰 Sprzedaż" },
  { id: "action", label: "🏁 Action Plan" },
];

/* ─── PLATFORM ANALYSIS ─── */
const platforms = [
  {
    name: "Web App",
    verdict: "🟢 PRIORYTET #1",
    priority: 1,
    color: "#22c55e",
    reason: "Najniższy próg wejścia dla klienta — zero instalacji. Demo → konwersja. SEO. Najszybszy time-to-market.",
    timeline: "2–3 tygodnie MVP",
    tech: "Next.js + React + Tailwind + shadcn/ui + Supabase auth",
    monetization: "Freemium → subskrypcja → enterprise",
    pros: ["Zero instalacji = max konwersja", "SEO / content marketing", "Stripe recurring billing natywnie", "Shared codebase z dashboard klienta", "A/B testing, analytics wbudowane"],
    cons: ["Wymaga backendu (hosting)", "Ograniczony dostęp do hardware (mikrofon OK, kamery limitowane)"],
  },
  {
    name: "Desktop (Broxeen / Tauri)",
    verdict: "🟡 PRIORYTET #2",
    priority: 2,
    color: "#f59e0b",
    reason: "Pełen dostęp do systemu: RTSP kamery, skan sieci, SSH, browser sessions. Kluczowy dla power users i wdrożeń on-premise.",
    timeline: "Już masz MVP — 1–2 tyg. na packaging + auto-update",
    tech: "Tauri 2 + React (istniejący Broxeen) + auto-updater",
    monetization: "Freemium + license key + premium skills",
    pros: ["Pełen dostęp do hardware i sieci", "RTSP, SSH, browser automation natywnie", "Offline mode (Ollama local)", "Idealne dla monitoring/security", "Już masz działający Broxeen"],
    cons: ["Wyższy próg wejścia (instalacja)", "Mniejsza skalowalność dystrybucji", "OS-specific builds (.deb, .exe, .dmg)"],
  },
  {
    name: "Mobile App",
    verdict: "🔴 NIE TERAZ",
    priority: 3,
    color: "#ef4444",
    reason: "Koszt development vs. wartość = niski ROI na starcie. Voice assistant na telefonie to commodity (Siri, Google, Alexa). Jedyny sensowny case: remote monitoring dashboard + push alerty z Broxeen.",
    timeline: "Odłóż na Q3-Q4 2026",
    tech: "React Native / Expo (współdzielenie komponentów z web) LUB PWA jako fast-track",
    monetization: "Companion app do subskrypcji desktop/web",
    pros: ["Push notifications z monitoringu kamer", "Remote dashboard — sprawdź status z telefonu", "Voice commands on-the-go"],
    cons: ["Wysokie koszty development (iOS + Android)", "App Store review = wolne", "Voice assistant na mobile to commodity", "Nie da się robić skan sieci / SSH z telefonu", "Konkurujesz z Siri/Google Assistant"],
    alternative: "PWA (Progressive Web App) — zainstaluj web app na telefonie. Zero kosztu, te same funkcje co web. Wystarczy na 90% przypadków mobile."
  },
];

/* ─── 3 APIs ─── */
const apis = [
  {
    name: "Voice API",
    subtitle: "Głosowa komunikacja z LLM",
    icon: "🎙️",
    color: "#8b5cf6",
    endpoint: "/api/v1/voice",
    desc: "WebSocket API do real-time voice conversation z CoreSkill. STT → intent → skill execution → TTS response. Klient mówi, system odpowiada głosem + wykonuje akcje.",
    routes: [
      { method: "WS", path: "/voice/stream", desc: "Real-time audio stream (bidirectional)" },
      { method: "POST", path: "/voice/transcribe", desc: "Audio file → tekst (STT)" },
      { method: "POST", path: "/voice/synthesize", desc: "Tekst → audio file (TTS)" },
      { method: "POST", path: "/voice/command", desc: "Audio → intent → execute → response" },
    ],
    pricing: [
      { tier: "Free", price: "0 PLN", limit: "100 minut/mies." },
      { tier: "Starter", price: "49 PLN/mies.", limit: "1000 minut + wake word" },
      { tier: "Pro", price: "149 PLN/mies.", limit: "5000 minut + custom wake word + priority" },
      { tier: "Enterprise", price: "Custom", limit: "Unlimited + SLA + on-premise" },
    ],
    usedBy: "Broxeen desktop, web app, klienci budujący voice boty",
    techStack: "FastAPI + WebSocket + Vosk/Whisper (STT) + Piper (TTS) + CoreSkill intent engine",
    readyIn: "2–3 tygodnie (masz już voice_loop.py + STT/TTS skills)",
  },
  {
    name: "LLM Proxy API",
    subtitle: "Multi-provider gateway",
    icon: "🔀",
    color: "#f59e0b",
    endpoint: "/api/v1/llm",
    desc: "Proxy agregujące wielu LLM providerów (OpenRouter, Ollama, HuggingFace) z UCB1 bandit routing, auto-fallback, cost optimization. Klient wysyła prompt, proxy wybiera najlepszy/najtańszy model.",
    routes: [
      { method: "POST", path: "/llm/chat", desc: "Chat completion (OpenAI-compatible)" },
      { method: "POST", path: "/llm/complete", desc: "Text completion" },
      { method: "GET", path: "/llm/models", desc: "Lista dostępnych modeli + stats" },
      { method: "GET", path: "/llm/usage", desc: "Zużycie tokeny / koszt per projekt" },
      { method: "POST", path: "/llm/optimize", desc: "Rekomendacja modelu dla zadania" },
    ],
    pricing: [
      { tier: "Free", price: "0 PLN", limit: "1000 requestów/mies. (free models only)" },
      { tier: "Dev", price: "49 PLN/mies.", limit: "10K req + paid models + dashboard" },
      { tier: "Team", price: "199 PLN/mies.", limit: "50K req + team management + analytics" },
      { tier: "Scale", price: "499 PLN/mies.", limit: "200K req + SLA + dedicated routing" },
    ],
    usedBy: "Polscy freelancerzy, startupy, software houses — zamiast OpenAI API bezpośrednio",
    techStack: "LiteLLM + FastAPI + UCB1 bandit_selector.py + provider_selector.py + Redis (rate limiting)",
    readyIn: "1 tydzień (LiteLLM + Twój bandit_selector = natychmiastowy MVP)",
    valueAdd: "Polska faktura VAT, PLN billing, auto-routing (nie przepłacasz za GPT-4 gdy Gemini Flash wystarczy), dashboard po polsku, fallback gdy provider padnie",
  },
  {
    name: "Skills Marketplace API",
    subtitle: "Rejestr i dystrybucja skilli",
    icon: "🧩",
    color: "#22c55e",
    endpoint: "/api/v1/skills",
    desc: "Registry dla skilli CoreSkill z wersjonowaniem, licencjonowaniem i auto-install. Developerzy publikują skille, klienci kupują/instalują. Stripe Connect dla revenue share.",
    routes: [
      { method: "GET", path: "/skills/search", desc: "Szukaj skilli (name, category, tags)" },
      { method: "GET", path: "/skills/:id", desc: "Szczegóły skilla + versions + stats" },
      { method: "POST", path: "/skills/:id/install", desc: "Instaluj skill (sprawdza licencję)" },
      { method: "POST", path: "/skills/publish", desc: "Opublikuj nowy skill" },
      { method: "GET", path: "/skills/:id/health", desc: "Health status zainstalowanego skilla" },
      { method: "POST", path: "/skills/:id/evolve", desc: "Trigger ewolucji skilla (premium)" },
    ],
    pricing: [
      { tier: "Free Skills", price: "0 PLN", limit: "echo, weather, calculator, time, notes" },
      { tier: "Per Skill", price: "29–199 PLN", limit: "Jednorazowy zakup, perpetual license" },
      { tier: "All-Access", price: "149 PLN/mies.", limit: "Wszystkie premium + updates + support" },
      { tier: "Publisher", price: "70/30 split", limit: "Publikuj skille, zarabiaj 70%" },
    ],
    usedBy: "Developerzy (kupujący i sprzedający), firmy chcące rozszerzyć CoreSkill",
    techStack: "FastAPI + Supabase (DB + auth) + Stripe Connect + S3 (skill packages) + skill_manager.py",
    readyIn: "3–4 tygodnie (skill_manager + manifest.json już masz, brakuje API layer + payment)",
  },
];

/* ─── USE CASES ─── */
const useCases = [
  {
    persona: "DevOps / SRE",
    icon: "🔧",
    technical: true,
    pain: "Nocne alerty, ręczne debugowanie, powtarzalne taski, monitoring rozproszony",
    value: "System który sam wykrywa problem, diagnozuje i naprawia — Ty śpisz, CoreSkill pracuje",
    howToSay: {
      tech: "CoreSkill to self-healing agent framework z 5-fazowym auto-repair pipeline. Integruje się z Twoim stackiem przez shell skill + SSH manager. Drift detection wykrywa regresje zanim user zgłosi ticket. UCB1 bandit routing oszczędza 40-60% na LLM costs.",
      nontech: null,
    },
    skills: ["shell", "devops", "network_scanner", "ssh_manager", "process_manager"],
    price: "199–499 PLN/mies.",
    voice: "Mów: „CoreSkill, status serverów" → dostaniesz raport health + alerty + sugestie napraw",
  },
  {
    persona: "Właściciel małej firmy",
    icon: "🏪",
    technical: false,
    pain: "Brak działu IT, nie wie co ma w sieci, boi się ataków, chce monitoring kamer",
    value: "Asystent IT który mówi po polsku, pilnuje sieci i kamer, informuje o problemach",
    howToSay: {
      tech: null,
      nontech: "Broxeen to Twój prywatny informatyk, który pilnuje firmy 24/7. Podłączasz kamery — on wykrywa ruch. Podłączasz do sieci — on sprawdza czy wszystko bezpieczne. Mówisz mu co potrzebujesz — on robi. Bez technicznej wiedzy.",
    },
    skills: ["camera_ai_monitor", "network_scanner", "web_search"],
    price: "99–299 PLN/mies. (Broxeen Pro)",
    voice: "Mów: „Heyken, co się dzieje w magazynie?" → dostaniesz raport z kamery + ostatnie zdarzenia",
  },
  {
    persona: "Programista / Freelancer",
    icon: "💻",
    technical: true,
    pain: "Drogie API OpenAI, brak fallbacku, potrzebuje szybko prototypować",
    value: "Tani LLM proxy z auto-routingiem + framework do budowania własnych agentów",
    howToSay: {
      tech: "OpenAI-compatible endpoint z UCB1 bandit routing — automatycznie wybiera najtańszy model który spełnia Twoje quality threshold. Fallback chain: free OpenRouter → local Ollama → paid API. Polska faktura, dashboard z kosztami per projekt.",
      nontech: null,
    },
    skills: ["llm_router", "benchmark", "web_search"],
    price: "49–199 PLN/mies. (LLM Proxy)",
    voice: null,
  },
  {
    persona: "E-commerce / Sprzedawca",
    icon: "🛒",
    technical: false,
    pain: "Ręczne sprawdzanie cen konkurencji, brak automatyzacji zamówień, kopiowanie danych między systemami",
    value: "Boty które same monitorują ceny i wypełniają formularze",
    howToSay: {
      tech: null,
      nontech: "Wyobraź sobie, że masz pracownika który siedzi 24/7 przed komputerem i sprawdza ceny u konkurencji. Gdy cena spadnie — dostajesz SMS. Gdy trzeba wrzucić 100 produktów na Allegro — robi to w 10 minut, nie w 3 godziny. To jest Broxeen.",
    },
    skills: ["browser_automation", "web_scraper_pro", "report_generator"],
    price: "149–799 PLN jednorazowo per bot",
    voice: "Mów: „Heyken, sprawdź ceny konkurencji na słuchawki Sony" → dostaniesz tabelę z cenami",
  },
  {
    persona: "Agencja Marketingowa",
    icon: "📊",
    technical: false,
    pain: "Raporty ręcznie, scraping social media, content generation, monitoring brandów",
    value: "Automatyczne raporty + scraping + content pipeline",
    howToSay: {
      tech: null,
      nontech: "CoreSkill zbiera dane z sieci, analizuje i robi za Ciebie raport w PDF. Zamiast 4 godzin ręcznej pracy — 5 minut. I uczy się Twoich preferencji — następny raport będzie jeszcze lepszy.",
    },
    skills: ["web_scraper_pro", "report_generator", "document_reader", "text_summarizer"],
    price: "499 PLN/mies. lub 2999 PLN jednorazowo (custom pipeline)",
    voice: "Mów: „Heyken, zrób raport tygodniowy z mediów o naszym kliencie XYZ"",
  },
  {
    persona: "Firma security / CCTV",
    icon: "📹",
    technical: true,
    pain: "Wiele kamer, brak AI detekcji, rozproszone lokalizacje",
    value: "AI monitoring z detekcją zdarzeń + auto-alerty + raport PDF",
    howToSay: {
      tech: "Broxeen obsługuje RTSP natywnie z ffmpeg backend. AI detekcja na YOLO/OpenCV — persons, vehicles, motion zones. SQLite event log z timestamp. API do integracji z NVR. Self-healing worker — jeśli stream padnie, automatycznie reconnect.",
      nontech: null,
    },
    skills: ["camera_ai_monitor", "network_scanner", "report_generator"],
    price: "999–4999 PLN jednorazowo + 199 PLN/mies. support",
    voice: "Mów: „Heyken, pokaż ostatnie zdarzenia z kamery przy bramie"",
  },
];

/* ─── SALES STRATEGY ─── */
const salesChannels = [
  {
    channel: "OLX Usługi → Audyt sieci + Boty",
    target: "Małe firmy PL",
    action: "3 ogłoszenia: 'Audyt bezpieczeństwa sieci 499 PLN', 'Bot monitoringu cen od 149 PLN', 'AI monitoring kamer'",
    timeline: "Jutro",
    expected: "2–5 klientów/mies., 1–3K PLN",
  },
  {
    channel: "Facebook Grupy → Demo + Oferta",
    target: "E-commerce, programiści PL",
    action: "Post z demo video (2 min) + komentarze z wartością. Grupy: E-commerce Polska, Python PL, Startups Poland",
    timeline: "Jutro",
    expected: "3–10 klientów/mies., 2–5K PLN",
  },
  {
    channel: "LinkedIn → Cold outreach do CTO/CEO",
    target: "Software houses, średnie firmy",
    action: "Oferta darmowego audytu sieci (lead magnet) → upsell monitoring/automatyzacja",
    timeline: "Tydzień 1",
    expected: "1–3 enterprise leads/mies., 5–15K PLN",
  },
  {
    channel: "Fiverr / Upwork → Gigi",
    target: "Global, ang.",
    action: "'Custom AI automation', 'Network security audit', 'Web scraping bot'. Cena $50–$500/gig",
    timeline: "Tydzień 1",
    expected: "5–15 gigs/mies., $500–$3000",
  },
  {
    channel: "GitHub + Product Hunt → OSS adoption",
    target: "Developerzy global",
    action: "Push CoreSkill na GitHub + README z demo GIF + Product Hunt launch",
    timeline: "Tydzień 2–3",
    expected: "Stars → docs traffic → LLM Proxy signups",
  },
  {
    channel: "YouTube PL → Tutorial SEO",
    target: "Polscy programiści",
    action: "3 filmy: 'Jak zautomatyzować...', 'AI monitoring kamer za 299 PLN', 'Tani LLM proxy'",
    timeline: "Tydzień 2–4",
    expected: "Long-tail traffic → conversions over months",
  },
];

function Section({ title, children }) {
  return (
    <div style={{ marginBottom: 40 }}>
      <h2 style={{ fontSize: 22, fontWeight: 800, margin: "0 0 20px 0", color: "#fafafa", borderBottom: "1px solid #27272a", paddingBottom: 12 }}>{title}</h2>
      {children}
    </div>
  );
}

function Card({ children, style = {} }) {
  return (
    <div style={{ background: "#111116", border: "1px solid #1e1e24", borderRadius: 14, padding: 20, ...style }}>
      {children}
    </div>
  );
}

function Tag({ children, color = "#6366f1" }) {
  return (
    <span style={{ display: "inline-block", background: color + "18", color, padding: "2px 10px", borderRadius: 999, fontSize: 11, fontWeight: 600, marginRight: 6, marginBottom: 4 }}>
      {children}
    </span>
  );
}

export default function MarketEntry() {
  const [tab, setTab] = useState("platforms");

  return (
    <div style={{ fontFamily: "'DM Sans', 'Segoe UI', system-ui, sans-serif", background: "#0a0a0f", color: "#e4e4e7", minHeight: "100vh", padding: "28px 20px" }}>
      <div style={{ maxWidth: 1000, margin: "0 auto" }}>
        {/* Header */}
        <div style={{ marginBottom: 32 }}>
          <h1 style={{ fontSize: 26, fontWeight: 800, margin: 0, background: "linear-gradient(135deg, #8b5cf6, #f59e0b, #22c55e)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            CoreSkill → Market Entry Strategy
          </h1>
          <p style={{ fontSize: 14, color: "#71717a", margin: "6px 0 0 0" }}>3 API · 6 grup docelowych · Web + Desktop + (nie)Mobile · Plan sprzedaży</p>
        </div>

        {/* Tabs */}
        <div style={{ display: "flex", gap: 4, marginBottom: 28, overflowX: "auto", paddingBottom: 4 }}>
          {sections.map((s) => (
            <button key={s.id} onClick={() => setTab(s.id)} style={{
              padding: "9px 16px", borderRadius: 8, border: "1px solid " + (tab === s.id ? "#f59e0b44" : "#27272a"),
              background: tab === s.id ? "#f59e0b12" : "transparent", color: tab === s.id ? "#fbbf24" : "#71717a",
              fontSize: 13, fontWeight: 600, cursor: "pointer", whiteSpace: "nowrap",
            }}>{s.label}</button>
          ))}
        </div>

        {/* ═══ PLATFORMS ═══ */}
        {tab === "platforms" && (
          <div>
            <p style={{ fontSize: 14, color: "#a1a1aa", marginBottom: 24, lineHeight: 1.7 }}>
              Priorytet: <strong style={{ color: "#22c55e" }}>Web najpierw</strong> (najszybsza konwersja), <strong style={{ color: "#f59e0b" }}>Desktop równolegle</strong> (już masz Broxeen), <strong style={{ color: "#ef4444" }}>Mobile = PWA, nie native app</strong>.
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              {platforms.map((p) => (
                <Card key={p.name}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", marginBottom: 14, flexWrap: "wrap", gap: 10 }}>
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                        <h3 style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>{p.name}</h3>
                        <Tag color={p.color}>{p.verdict}</Tag>
                      </div>
                      <p style={{ fontSize: 13, color: "#a1a1aa", margin: "6px 0 0 0", lineHeight: 1.6 }}>{p.reason}</p>
                    </div>
                    <div style={{ fontSize: 12, color: "#52525b", textAlign: "right" }}>
                      <div style={{ fontWeight: 600, color: "#d4d4d8" }}>{p.timeline}</div>
                      <div style={{ fontFamily: "monospace", marginTop: 4 }}>{p.tech}</div>
                    </div>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 12 }}>
                    <div style={{ background: "#0a0a0f", borderRadius: 8, padding: 12 }}>
                      <div style={{ fontSize: 11, fontWeight: 600, color: "#22c55e", marginBottom: 6 }}>✅ ZALETY</div>
                      {p.pros.map((pr, i) => <div key={i} style={{ fontSize: 12, color: "#a1a1aa", lineHeight: 1.8 }}>• {pr}</div>)}
                    </div>
                    <div style={{ background: "#0a0a0f", borderRadius: 8, padding: 12 }}>
                      <div style={{ fontSize: 11, fontWeight: 600, color: "#ef4444", marginBottom: 6 }}>⚠️ WADY</div>
                      {p.cons.map((c, i) => <div key={i} style={{ fontSize: 12, color: "#a1a1aa", lineHeight: 1.8 }}>• {c}</div>)}
                    </div>
                  </div>
                  {p.alternative && (
                    <div style={{ background: "#f59e0b0a", border: "1px solid #f59e0b22", borderRadius: 8, padding: 12, fontSize: 13, color: "#fbbf24" }}>
                      💡 <strong>Alternatywa:</strong> {p.alternative}
                    </div>
                  )}
                  <div style={{ marginTop: 10, fontSize: 12, color: "#52525b" }}>
                    <strong>Monetyzacja:</strong> {p.monetization}
                  </div>
                </Card>
              ))}
            </div>
          </div>
        )}

        {/* ═══ 3 APIs ═══ */}
        {tab === "apis" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
            <div style={{ padding: 16, background: "#18181b", borderRadius: 12, border: "1px solid #27272a" }}>
              <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 8px 0", color: "#fafafa" }}>🏗️ Architektura: 1 gateway, 3 domenowe API</h3>
              <pre style={{ fontSize: 12, color: "#a1a1aa", margin: 0, lineHeight: 1.8, overflow: "auto" }}>{`
┌─────────────────────────────────────────────────────────┐
│  API Gateway (FastAPI + Auth + Rate Limiting + Billing) │
│  gateway.coreskill.ai                                    │
├─────────────┬─────────────────┬─────────────────────────┤
│ /api/v1/    │ /api/v1/llm     │ /api/v1/skills          │
│   voice     │                 │                         │
│             │                 │                         │
│ WebSocket   │ OpenAI-compat   │ Registry +              │
│ STT → Intent│ UCB1 routing    │ Install +               │
│ → Skill     │ Free→Local→Paid │ License check           │
│ → TTS       │ Cost dashboard  │ Publish +               │
│             │                 │ Revenue share            │
├─────────────┴─────────────────┴─────────────────────────┤
│  CoreSkill Engine (evo-engine core)                      │
│  intent_engine + skill_manager + evo_engine +            │
│  auto_repair + bandit_selector + provider_chain          │
├─────────────────────────────────────────────────────────┤
│  Data Layer: Supabase (auth+DB) + Redis + S3 (skills)   │
│  Billing: Stripe (subscriptions + metered + Connect)     │
└─────────────────────────────────────────────────────────┘`}</pre>
            </div>
            {apis.map((api) => (
              <Card key={api.name} style={{ borderLeft: `3px solid ${api.color}` }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
                  <span style={{ fontSize: 24 }}>{api.icon}</span>
                  <div>
                    <h3 style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>{api.name}</h3>
                    <span style={{ fontSize: 12, color: "#71717a" }}>{api.subtitle}</span>
                  </div>
                  <Tag color={api.color}>{api.endpoint}</Tag>
                  <Tag color="#22c55e">Ready: {api.readyIn}</Tag>
                </div>
                <p style={{ fontSize: 13, color: "#a1a1aa", lineHeight: 1.7, margin: "10px 0 16px 0" }}>{api.desc}</p>

                {api.valueAdd && (
                  <div style={{ background: "#f59e0b0a", border: "1px solid #f59e0b22", borderRadius: 8, padding: 12, marginBottom: 16, fontSize: 13, color: "#fbbf24" }}>
                    💎 <strong>Value-add vs. raw OpenAI/OpenRouter:</strong> {api.valueAdd}
                  </div>
                )}

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                  <div>
                    <div style={{ fontSize: 11, fontWeight: 700, color: "#52525b", textTransform: "uppercase", marginBottom: 8 }}>Endpoints</div>
                    {api.routes.map((r, i) => (
                      <div key={i} style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 6 }}>
                        <span style={{ fontFamily: "monospace", fontSize: 10, fontWeight: 700, color: r.method === "WS" ? "#8b5cf6" : r.method === "POST" ? "#22c55e" : "#3b82f6", background: "#0a0a0f", padding: "2px 6px", borderRadius: 4, minWidth: 38, textAlign: "center" }}>{r.method}</span>
                        <span style={{ fontFamily: "monospace", fontSize: 11, color: "#d4d4d8" }}>{r.path}</span>
                        <span style={{ fontSize: 11, color: "#71717a" }}>— {r.desc}</span>
                      </div>
                    ))}
                  </div>
                  <div>
                    <div style={{ fontSize: 11, fontWeight: 700, color: "#52525b", textTransform: "uppercase", marginBottom: 8 }}>Cennik</div>
                    {api.pricing.map((p, i) => (
                      <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "6px 10px", borderRadius: 6, background: i === 0 ? "transparent" : "#0a0a0f", marginBottom: 4 }}>
                        <span style={{ fontSize: 12, fontWeight: 600, color: "#d4d4d8" }}>{p.tier}</span>
                        <span style={{ fontSize: 12, fontWeight: 700, color: "#fbbf24" }}>{p.price}</span>
                        <span style={{ fontSize: 11, color: "#71717a" }}>{p.limit}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div style={{ marginTop: 12, fontSize: 12, color: "#52525b" }}>
                  <strong>Tech:</strong> {api.techStack} · <strong>Kto używa:</strong> {api.usedBy}
                </div>
              </Card>
            ))}
          </div>
        )}

        {/* ═══ USE CASES ═══ */}
        {tab === "usecases" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            {useCases.map((uc, i) => (
              <Card key={i}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", marginBottom: 12, flexWrap: "wrap", gap: 8 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{ fontSize: 28 }}>{uc.icon}</span>
                    <div>
                      <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>{uc.persona}</h3>
                      <Tag color={uc.technical ? "#3b82f6" : "#22c55e"}>{uc.technical ? "Techniczny" : "Nietechniczny"}</Tag>
                    </div>
                  </div>
                  <div style={{ fontSize: 16, fontWeight: 800, color: "#fbbf24" }}>{uc.price}</div>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 14 }}>
                  <div style={{ background: "#ef44440a", borderRadius: 8, padding: 12 }}>
                    <div style={{ fontSize: 11, fontWeight: 700, color: "#ef4444", marginBottom: 6 }}>😤 BÓL</div>
                    <div style={{ fontSize: 13, color: "#d4d4d8", lineHeight: 1.6 }}>{uc.pain}</div>
                  </div>
                  <div style={{ background: "#22c55e0a", borderRadius: 8, padding: 12 }}>
                    <div style={{ fontSize: 11, fontWeight: 700, color: "#22c55e", marginBottom: 6 }}>✨ WARTOŚĆ</div>
                    <div style={{ fontSize: 13, color: "#d4d4d8", lineHeight: 1.6 }}>{uc.value}</div>
                  </div>
                </div>

                <div style={{ background: "#0a0a0f", borderRadius: 8, padding: 14, marginBottom: 12 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: "#8b5cf6", marginBottom: 8 }}>
                    💬 JAK MÓWIĆ DO {uc.technical ? "TECHNICZNEGO" : "NIETECHNICZNEGO"}
                  </div>
                  <div style={{ fontSize: 13, color: "#d4d4d8", lineHeight: 1.7, fontStyle: "italic" }}>
                    „{uc.howToSay.tech || uc.howToSay.nontech}"
                  </div>
                </div>

                {uc.voice && (
                  <div style={{ background: "#8b5cf60a", border: "1px solid #8b5cf622", borderRadius: 8, padding: 12, marginBottom: 10, fontSize: 13 }}>
                    <span style={{ color: "#8b5cf6", fontWeight: 600 }}>🎙️ Voice UX:</span>{" "}
                    <span style={{ color: "#d4d4d8" }}>{uc.voice}</span>
                  </div>
                )}

                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {uc.skills.map((s) => <Tag key={s} color="#71717a">{s}</Tag>)}
                </div>
              </Card>
            ))}
          </div>
        )}

        {/* ═══ MESSAGING ═══ */}
        {tab === "messaging" && (
          <div>
            <Section title="Jak mówić o CoreSkill — dwa języki, jeden produkt">
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 32 }}>
                <Card style={{ borderTop: "3px solid #3b82f6" }}>
                  <h3 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 12px 0", color: "#3b82f6" }}>🔧 Dla technicznego</h3>
                  <div style={{ fontSize: 13, color: "#d4d4d8", lineHeight: 1.8 }}>
                    <p style={{ margin: "0 0 12px 0" }}><strong>Pitch (10 sek.):</strong> „Self-healing agent framework z ewolucyjnymi skillami, 3-tier intent classification i UCB1 bandit LLM routing. MIT license, local-first, production-ready."</p>
                    <p style={{ margin: "0 0 12px 0" }}><strong>Elevator (30 sek.):</strong> „CoreSkill to framework do budowania AI agentów, które się same naprawiają. Masz 40+ modułów — od ML intent detection, przez evolutionary code mutation, po proactive health monitoring. Routing LLM idzie przez UCB1 bandit — automatycznie wybiera najtańszego providera który dowozi quality. Działa offline na Ollama. MIT license."</p>
                    <p style={{ margin: "0 0 12px 0" }}><strong>Słowa kluczowe:</strong> self-healing, evolutionary, MLOps, UCB1 bandit, intent classification, skill versioning, drift detection, quality gates, tiered fallback, zero-cost LLM</p>
                    <p style={{ margin: 0 }}><strong>Demo hook:</strong> „Pokażę Ci jak CoreSkill sam naprawia zepsuty skill w 30 sekund — bez interwencji człowieka."</p>
                  </div>
                </Card>
                <Card style={{ borderTop: "3px solid #22c55e" }}>
                  <h3 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 12px 0", color: "#22c55e" }}>🏪 Dla nietechnicznego</h3>
                  <div style={{ fontSize: 13, color: "#d4d4d8", lineHeight: 1.8 }}>
                    <p style={{ margin: "0 0 12px 0" }}><strong>Pitch (10 sek.):</strong> „Broxeen to Twój prywatny informatyk, który pracuje 24/7, mówi po polsku i pilnuje Twojej firmy."</p>
                    <p style={{ margin: "0 0 12px 0" }}><strong>Elevator (30 sek.):</strong> „Podłączasz Broxeen do swojej sieci i kamer. Od teraz sam sprawdza czy wszystko działa, wykrywa problemy zanim się pojawią, i informuje Cię gdy coś wymaga uwagi. Mówisz mu po polsku — głosem lub tekstem — co potrzebujesz. Nie musisz nic wiedzieć o IT."</p>
                    <p style={{ margin: "0 0 12px 0" }}><strong>Słowa kluczowe:</strong> prywatny informatyk, pilnuje 24/7, mówi po polsku, sam się uczy, monitoring, bezpieczeństwo, automatyzacja, oszczędność czasu</p>
                    <p style={{ margin: 0 }}><strong>Demo hook:</strong> „Powiem mu głosem: 'Heyken, skanuj sieć' — za 30 sekund zobaczysz każde urządzenie w Twojej firmie."</p>
                  </div>
                </Card>
              </div>
            </Section>

            <Section title="Voice UX — jak nietechniczny użytkownik to używa">
              <Card>
                <div style={{ fontSize: 13, color: "#d4d4d8", lineHeight: 1.8 }}>
                  <p style={{ margin: "0 0 16px 0" }}>Voice to Twój <strong style={{ color: "#8b5cf6" }}>najsilniejszy differentiator dla nietechnicznych</strong> — żaden konkurent (LangGraph, CrewAI, AutoGPT) nie ma natywnego voice loop. Broxeen ma „heyken" wake word.</p>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                    {[
                      { say: "Heyken, co się dzieje w sieci?", get: "Raport: 12 urządzeń online, 2 nowe, żadnych alertów." },
                      { say: "Heyken, pokaż kamery", get: "Masz 3 aktywne kamery. Kamera magazyn — ostatni ruch 14:23. Pokazać live?" },
                      { say: "Heyken, sprawdź ceny słuchawek Sony na Allegro", get: "Najtańsza oferta: Sony WH-1000XM5 za 1299 PLN. Wczoraj było 1349. Spadek 3.7%." },
                      { say: "Heyken, czy serwer działa?", get: "Serwer 192.168.1.100 — ping 2ms, uptime 47 dni, CPU 23%, dysk 67% wolny. Wszystko OK." },
                      { say: "Heyken, zrób backup bazy danych", get: "Backup uruchomiony. Szacowany czas: 4 minuty. Powiadomię gdy skończę." },
                      { say: "Heyken, przypomnij mi jutro o spotkaniu z klientem", get: "Zapisane. Przypomnę jutro o 9:00 rano." },
                    ].map((ex, i) => (
                      <div key={i} style={{ background: "#0a0a0f", borderRadius: 8, padding: 12 }}>
                        <div style={{ fontSize: 12, color: "#8b5cf6", fontWeight: 600, marginBottom: 6 }}>🎙️ Mówisz:</div>
                        <div style={{ fontSize: 13, color: "#fafafa", marginBottom: 8, fontStyle: "italic" }}>„{ex.say}"</div>
                        <div style={{ fontSize: 12, color: "#22c55e", fontWeight: 600, marginBottom: 4 }}>🔊 Broxeen odpowiada:</div>
                        <div style={{ fontSize: 12, color: "#a1a1aa" }}>„{ex.get}"</div>
                      </div>
                    ))}
                  </div>
                </div>
              </Card>
            </Section>
          </div>
        )}

        {/* ═══ SALES ═══ */}
        {tab === "sales" && (
          <div>
            <Section title="Jak sprzedawać — konkretne kanały i akcje">
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {salesChannels.map((sc, i) => (
                  <Card key={i}>
                    <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 3fr 1.5fr", gap: 16, alignItems: "start" }}>
                      <div>
                        <h4 style={{ fontSize: 14, fontWeight: 700, margin: 0, color: "#fafafa" }}>{sc.channel}</h4>
                        <Tag color="#6366f1">{sc.target}</Tag>
                      </div>
                      <Tag color="#f59e0b">{sc.timeline}</Tag>
                      <div style={{ fontSize: 12, color: "#a1a1aa", lineHeight: 1.6 }}>{sc.action}</div>
                      <div style={{ fontSize: 13, fontWeight: 700, color: "#22c55e", textAlign: "right" }}>{sc.expected}</div>
                    </div>
                  </Card>
                ))}
              </div>
            </Section>

            <Section title="Pakiety ofertowe — gotowe do kopiowania">
              {[
                {
                  name: "🔍 Pakiet AUDYT",
                  price: "499 PLN jednorazowo",
                  desc: "Profesjonalny audyt sieci Twojej firmy. Wykryję wszystkie urządzenia, otwarte porty, potencjalne zagrożenia. Dostarczę raport PDF z rekomendacjami.",
                  includes: "Skan sieci + identyfikacja urządzeń + check portów + raport PDF 10-15 stron + 15 min konsultacja",
                  postOn: "OLX, Facebook (grupy małych firm), LinkedIn",
                },
                {
                  name: "📷 Pakiet MONITORING",
                  price: "299 PLN setup + 99 PLN/mies.",
                  desc: "AI monitoring kamer Twojej firmy. Detekcja ruchu, osób, pojazdów. Powiadomienia na telefon. Bez abonamentów u operatorów.",
                  includes: "Konfiguracja do 5 kamer + AI detekcja + alerty email/push + dashboard + 1h support/mies.",
                  postOn: "OLX, Facebook (grupy CCTV, małe firmy), lokalne fora",
                },
                {
                  name: "🤖 Pakiet BOT",
                  price: "od 149 PLN",
                  desc: "Dedykowany bot automatyzujący Twoją pracę. Monitoring cen, scraping danych, auto-wypełnianie formularzy. Dostosowany do Twoich potrzeb.",
                  includes: "Analiza potrzeb + custom bot + dokumentacja + 7 dni support",
                  postOn: "OLX, Facebook (e-commerce, marketing), Fiverr",
                },
              ].map((pkg, i) => (
                <Card key={i} style={{ marginBottom: 16, borderLeft: "3px solid #fbbf24" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                    <h4 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>{pkg.name}</h4>
                    <span style={{ fontSize: 18, fontWeight: 800, color: "#fbbf24" }}>{pkg.price}</span>
                  </div>
                  <div style={{ fontSize: 13, color: "#d4d4d8", lineHeight: 1.7, marginBottom: 10 }}>
                    <strong style={{ color: "#fafafa" }}>Opis do ogłoszenia:</strong> „{pkg.desc}"
                  </div>
                  <div style={{ fontSize: 12, color: "#a1a1aa", marginBottom: 6 }}>
                    <strong>Zawiera:</strong> {pkg.includes}
                  </div>
                  <div style={{ fontSize: 12, color: "#71717a" }}>
                    <strong>Gdzie publikować:</strong> {pkg.postOn}
                  </div>
                </Card>
              ))}
            </Section>
          </div>
        )}

        {/* ═══ ACTION PLAN ═══ */}
        {tab === "action" && (
          <div>
            <Section title="Plan działania — od zera do pierwszych przychodów">
              <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                {[
                  { phase: "TYDZIEŃ 1", color: "#ef4444", title: "Landing + pierwsze ogłoszenia", tasks: [
                    "Dzień 1: Carrd.co landing z 3 pakietami (Audyt, Monitoring, Bot) + Stripe links",
                    "Dzień 2: 3 ogłoszenia OLX + 3 posty na FB grupach (wartość + CTA)",
                    "Dzień 3: Demo video 2 min (skan sieci + live kamera) → YouTube + LinkedIn",
                    "Dzień 4: LiteLLM proxy na Hetzner → api.coreskill.ai/v1/llm + Stripe metered",
                    "Dzień 5: Gig Fiverr + 10 cold DM LinkedIn ('darmowy audyt sieci 15 min')",
                  ]},
                  { phase: "TYDZIEŃ 2–3", color: "#f59e0b", title: "API + Skills + pierwsi klienci", tasks: [
                    "FastAPI gateway z auth (Supabase) — /voice, /llm, /skills endpointy",
                    "Opakuj 5 premium skills (.zip + README + manifest) — sprzedaż przez Stripe",
                    "Web dashboard MVP (React + shadcn) — signup, API keys, usage, billing",
                    "Blog post: 'Jak zaoszczędzić 60% na LLM API z inteligentnym routingiem'",
                    "Iterate na feedbacku od pierwszych klientów OLX/FB",
                  ]},
                  { phase: "MIESIĄC 2", color: "#22c55e", title: "Skalowanie + Product Hunt", tasks: [
                    "CoreSkill na GitHub (public) z dobrym README + demo GIF + getting started",
                    "Product Hunt launch — 'Self-healing AI agent framework'",
                    "Skills Marketplace MVP — API /skills/search, /install, /publish",
                    "YouTube seria: 3 tutoriale po polsku (skan sieci, LLM proxy, voice bot)",
                    "Pierwsze pakiety wdrożeniowe (5–15K PLN per klient)",
                  ]},
                  { phase: "MIESIĄC 3–6", color: "#8b5cf6", title: "Rynek EU + Enterprise", tasks: [
                    "Angielska wersja landing + docs (Mintlify/Docusaurus)",
                    "PWA jako 'mobile app' (zero kosztu, pełna funkcjonalność web)",
                    "SOC 2 readiness (audit logging, encryption at rest — masz audit w TODO)",
                    "DACH market entry (Niemcy = najwyższy budżet na DevOps tooling w EU)",
                    "Enterprise tier: BYOC, SSO/SAML, SLA, dedicated support",
                  ]},
                ].map((p) => (
                  <div key={p.phase} style={{ background: "#111116", border: "1px solid #1e1e24", borderLeft: `4px solid ${p.color}`, borderRadius: "0 12px 12px 0", padding: 20, marginBottom: 12 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
                      <span style={{ fontSize: 11, fontWeight: 800, color: p.color, letterSpacing: "0.05em" }}>{p.phase}</span>
                      <h4 style={{ fontSize: 15, fontWeight: 700, margin: 0, color: "#fafafa" }}>{p.title}</h4>
                    </div>
                    {p.tasks.map((t, i) => (
                      <div key={i} style={{ display: "flex", gap: 10, alignItems: "flex-start", marginBottom: 6 }}>
                        <span style={{ fontSize: 14, lineHeight: "20px" }}>☐</span>
                        <span style={{ fontSize: 13, color: "#d4d4d8", lineHeight: 1.6 }}>{t}</span>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </Section>

            <Card style={{ borderTop: "3px solid #fbbf24", marginTop: 20 }}>
              <h3 style={{ fontSize: 16, fontWeight: 800, margin: "0 0 12px 0", color: "#fbbf24" }}>🎯 TL;DR — Co robisz JUTRO</h3>
              <div style={{ fontSize: 14, color: "#d4d4d8", lineHeight: 1.8 }}>
                <strong>1.</strong> Carrd.co landing → 3 pakiety → Stripe payment links <span style={{ color: "#71717a" }}>(2h)</span><br />
                <strong>2.</strong> OLX: „Audyt bezpieczeństwa sieci — 499 PLN" <span style={{ color: "#71717a" }}>(15 min)</span><br />
                <strong>3.</strong> Facebook grupa e-commerce: post z wartością + oferta bota do cen <span style={{ color: "#71717a" }}>(30 min)</span><br />
                <strong>4.</strong> LinkedIn: „Oferuję darmowy 15-min audyt sieci Twojej firmy" → cold DM do 10 osób <span style={{ color: "#71717a" }}>(1h)</span><br />
                <br />
                <strong style={{ color: "#22c55e" }}>Spodziewany wynik tygodnia 1:</strong> 1–3 płatnych klientów, 500–1500 PLN, bezcenny feedback na product-market fit.
              </div>
            </Card>
          </div>
        )}

        <div style={{ marginTop: 48, padding: 20, borderTop: "1px solid #1e1e24", fontSize: 11, color: "#3f3f46", textAlign: "center" }}>
          CoreSkill Market Entry Strategy · Marzec 2026 · Wersja głosowa: „Heyken, pokaż strategię wejścia na rynek"
        </div>
      </div>
    </div>
  );
}
