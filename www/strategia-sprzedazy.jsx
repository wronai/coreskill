import { useState } from "react";

const phases = [
  {
    id: "week1",
    title: "Tydzień 1–2",
    subtitle: "Pierwsze przychody",
    color: "#ef4444",
    revenue: "500–2000 PLN/mies.",
    items: [
      {
        name: "LLM Proxy + API Key Reselling",
        desc: "Uruchom proxy (LiteLLM/OpenRouter) z polskim landing page. Sprzedaj dostęp do taniego LLM API ze swoim value-add: polskie prompty, auto-routing, fallback.",
        price: "49 PLN/mies. (1000 req) → 149 PLN (10K req) → 499 PLN (unlimited)",
        target: "Polscy freelancerzy, startupy, studenci AI",
        effort: "2–3 dni setup",
        tech: "LiteLLM + Stripe + landing page",
      },
      {
        name: "Browser Automation as a Service",
        desc: "Opakuj Broxeen browser sessions w gotowe skrypty automatyzacji: monitoring cen, scraping ofert, auto-fill formularzy. Sprzedawaj jako gotowe \"boty\".",
        price: "99–299 PLN jednorazowo per bot / 49 PLN/mies. za hosting",
        target: "E-commerce, agencje marketingowe, handlowcy",
        effort: "1 tydzień na 3–5 botów",
        tech: "Broxeen + Playwright/Puppeteer sessions",
      },
    ],
  },
  {
    id: "month1",
    title: "Miesiąc 1–2",
    subtitle: "Stały MRR",
    color: "#f59e0b",
    revenue: "3000–8000 PLN/mies.",
    items: [
      {
        name: "Broxeen Pro — Monitoring Kamer AI",
        desc: "Pakiet desktop app + 5 kamer + AI detekcja (ruch, osoby, pojazdy). Gotowy produkt dla małych firm, warsztatów, sklepów, magazynów.",
        price: "199 PLN/mies. (do 5 kamer) → 499 PLN/mies. (do 20 kamer) → 999 PLN jednorazowo (lifetime, self-hosted)",
        target: "Małe firmy, warsztaty, sklepy, biura w PL",
        effort: "2 tygodnie na packaging + onboarding",
        tech: "Broxeen + RTSP + AI model (YOLO/OpenCV)",
      },
      {
        name: "Skills Marketplace — MVP",
        desc: "Rejestr skilli z podziałem: Free (echo, weather, calculator) → Premium (browser automation, network scan, document reader, DevOps). Jednorazowy zakup lub subskrypcja.",
        price: "Free tier → 29 PLN/skill → 149 PLN/mies. (all-access)",
        target: "Developerzy, DevOps, sysadmini",
        effort: "2 tygodnie na portal + payment",
        tech: "Next.js storefront + Stripe + skill registry API",
      },
    ],
  },
  {
    id: "quarter1",
    title: "Kwartał 1–2",
    subtitle: "Skalowanie",
    color: "#22c55e",
    revenue: "10K–30K PLN/mies.",
    items: [
      {
        name: "CoreSkill Cloud — Managed Platform",
        desc: "Hostowany evo-engine z dashboard, monitoring, skill marketplace. Klient deployuje agenty bez własnej infrastruktury.",
        price: "0 PLN (500 exec/mies.) → 299 PLN (5K exec) → 999 PLN (25K exec) → Enterprise custom",
        target: "Zespoły DevOps, software houses, startupy AI",
        effort: "1–2 miesiące na MVP cloud",
        tech: "Docker + K8s + dashboard React + Stripe metered billing",
      },
      {
        name: "Pakiety wdrożeniowe (consulting)",
        desc: "Wdrożenie automatyzacji u klienta: monitoring sieci, browser boty, integracje. Sprzedaż bezpośrednia w PL, potem EU.",
        price: "5000–15 000 PLN per wdrożenie + 499 PLN/mies. support",
        target: "Średnie firmy, agencje, software houses",
        effort: "Per projekt",
        tech: "Broxeen + evo-engine + custom skills",
      },
    ],
  },
];

const quickWins = [
  {
    what: "🤖 Bot monitoringu cen",
    who: "Sprzedawcy Allegro/Amazon",
    price: "149 PLN",
    time: "2 dni",
    desc: "Automatyczne śledzenie cen konkurencji na Allegro/Amazon. Alert email/SMS gdy cena spadnie.",
  },
  {
    what: "📷 Zestaw monitoring 1 kamera",
    who: "Właściciele warsztatów/sklepów",
    price: "299 PLN setup + 49 PLN/mies.",
    time: "1 dzień",
    desc: "Broxeen + tania kamera IP + AI detekcja ruchu. Powiadomienia na telefon.",
  },
  {
    what: "🔍 Audyt sieci + raport",
    who: "Małe firmy bez IT",
    price: "499 PLN jednorazowo",
    time: "1 dzień",
    desc: "Skan sieci Broxeen → raport PDF: wszystkie urządzenia, otwarte porty, zagrożenia, rekomendacje.",
  },
  {
    what: "📝 Bot auto-wypełniania formularzy",
    who: "Księgowi, HR, administracja",
    price: "199 PLN/mies.",
    time: "3 dni",
    desc: "Automatyczne wypełnianie powtarzalnych formularzy online (US, ZUS, GUS) z danych Excel/CSV.",
  },
  {
    what: "🌐 Web scraper na zamówienie",
    who: "Agencje marketingowe, researchers",
    price: "299–799 PLN per scraper",
    time: "2–5 dni",
    desc: "Dedykowany scraper: nieruchomości, oferty pracy, przetargi. Dane do CSV/Google Sheets.",
  },
  {
    what: "🔑 LLM API dla polskich devów",
    who: "Freelancerzy, startupy",
    price: "49 PLN/mies.",
    time: "3 dni setup",
    desc: "Proxy do GPT-4/Claude/Gemini z polskim dashboardem, fakturą PL, limity per projekt.",
  },
];

const premiumSkills = [
  { name: "browser_automation", cat: "Automatyzacja", price: "99 PLN", demand: "🔥🔥🔥", desc: "Playwright sessions, form fill, screenshot, PDF" },
  { name: "network_scanner_pro", cat: "Bezpieczeństwo", price: "149 PLN", demand: "🔥🔥🔥", desc: "Pełny skan + vuln check + raport PDF" },
  { name: "camera_ai_monitor", cat: "Monitoring", price: "199 PLN", demand: "🔥🔥", desc: "YOLO detekcja + alerty + timeline zdarzeń" },
  { name: "document_ocr_reader", cat: "Dokumenty", price: "79 PLN", demand: "🔥🔥", desc: "OCR + ekstrakcja danych z faktur/umów" },
  { name: "devops_deploy", cat: "DevOps", price: "149 PLN", demand: "🔥🔥", desc: "Auto-deploy, health check, rollback" },
  { name: "web_scraper_pro", cat: "Data", price: "129 PLN", demand: "🔥🔥🔥", desc: "Anti-bot bypass, pagination, proxy rotation" },
  { name: "llm_router_smart", cat: "AI", price: "99 PLN", demand: "🔥🔥", desc: "UCB1 bandit routing + cost optimization" },
  { name: "ssh_manager", cat: "Infrastruktura", price: "79 PLN", demand: "🔥", desc: "Multi-server SSH, batch commands, monitoring" },
  { name: "backup_agent", cat: "Infrastruktura", price: "99 PLN", demand: "🔥🔥", desc: "Auto-backup do S3/GCS/local, szyfrowanie, harmonogram" },
  { name: "report_generator", cat: "Business", price: "149 PLN", demand: "🔥🔥", desc: "Auto-raporty PDF/DOCX z danych, szablony, AI podsumowania" },
];

const channels = [
  { ch: "OLX / Usługi", cost: "0 PLN", reach: "Natychmiast", desc: "Ogłoszenia: 'Automatyzacja IT', 'Monitoring kamer AI', 'Boty do scrapingu'" },
  { ch: "Grupy Facebook", cost: "0 PLN", reach: "1–3 dni", desc: "Polskie grupy: programowanie, ecommerce, małe firmy, startups PL. Daj wartość, potem ofertę" },
  { ch: "LinkedIn PL", cost: "0 PLN", reach: "1 tydzień", desc: "Posty o automatyzacji, case study, demo video. CTO/CEO małych firm" },
  { ch: "Micro-landing (Carrd)", cost: "19 PLN/rok", reach: "1 dzień setup", desc: "Szybka strona z ofertą + Stripe payment link. carrd.co lub landing.ai" },
  { ch: "Fiverr / Upwork", cost: "0 PLN", reach: "1 tydzień", desc: "Gig: 'Custom AI bot', 'Network security audit', 'Web scraping service'" },
  { ch: "GitHub + Product Hunt", cost: "0 PLN", reach: "2–4 tyg.", desc: "Open-source → star gathering → Product Hunt launch → paid conversions" },
  { ch: "YouTube PL (demo)", cost: "0 PLN", reach: "2–4 tyg.", desc: "Krótkie demo: 'Jak zautomatyzować X w 5 minut'. SEO na polskie frazy" },
];

const techStack = [
  { layer: "Landing / Storefront", rec: "Carrd.co → Next.js", reason: "Carrd na start (19 PLN/rok, 1 dzień). Potem Next.js z Tailwind." },
  { layer: "Payments", rec: "Stripe / Przelewy24", reason: "Stripe = globalny + recurring. P24 = polski standard, niski próg." },
  { layer: "LLM Proxy", rec: "LiteLLM + OpenRouter", reason: "LiteLLM OSS proxy. OpenRouter jako fallback. Własny wrapper z metrami." },
  { layer: "Skill Registry", rec: "Supabase + REST API", reason: "Supabase (darmowy tier) jako DB + auth. REST endpoint do skill install." },
  { layer: "Dashboard klienta", rec: "React + shadcn/ui", reason: "Wykorzystaj istniejący stack z Broxeen. shadcn = szybki enterprise UI." },
  { layer: "Deployment", rec: "Hetzner VPS (€4.5/mies.)", reason: "Najtańszy EU hosting z dobrym uptime. Docker Compose na start." },
  { layer: "Monitoring", rec: "Broxeen self-eat", reason: "Używaj własnego evo-engine do monitorowania produkcji = best demo." },
  { layer: "Dokumentacja", rec: "Mintlify / Docusaurus", reason: "Profesjonalne docs = zaufanie. Mintlify free tier lub Docusaurus OSS." },
];

function Badge({ children, color = "#6366f1" }) {
  return (
    <span
      style={{
        background: color + "18",
        color: color,
        padding: "2px 10px",
        borderRadius: "999px",
        fontSize: "12px",
        fontWeight: 600,
        letterSpacing: "0.02em",
      }}
    >
      {children}
    </span>
  );
}

export default function Strategy() {
  const [tab, setTab] = useState("phases");

  const tabs = [
    { id: "phases", label: "🚀 Fazy launchu" },
    { id: "quickwins", label: "⚡ Quick Wins" },
    { id: "skills", label: "🧩 Premium Skills" },
    { id: "channels", label: "📢 Kanały sprzedaży" },
    { id: "tech", label: "🔧 Tech Stack" },
  ];

  return (
    <div style={{ fontFamily: "'DM Sans', 'Segoe UI', system-ui, sans-serif", background: "#0a0a0f", color: "#e4e4e7", minHeight: "100vh", padding: "32px 24px" }}>
      <div style={{ maxWidth: 960, margin: "0 auto" }}>
        {/* Header */}
        <div style={{ marginBottom: 40 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
            <div style={{ width: 40, height: 40, borderRadius: 10, background: "linear-gradient(135deg, #ef4444, #f59e0b)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20 }}>⚡</div>
            <div>
              <h1 style={{ fontSize: 28, fontWeight: 800, margin: 0, background: "linear-gradient(135deg, #ef4444, #f59e0b, #22c55e)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
                Strategia Go-to-Market
              </h1>
              <p style={{ fontSize: 13, color: "#71717a", margin: 0 }}>evo-engine + Broxeen → przychody w 7 dni</p>
            </div>
          </div>
          <p style={{ fontSize: 15, color: "#a1a1aa", lineHeight: 1.7, margin: "16px 0 0 0" }}>
            Strategia "revenue-first": zacznij od natychmiastowych przychodów w PL (OLX, Facebook, LinkedIn), skaluj przez marketplace skills + LLM proxy, potem wchodź na EU/global z managed cloud platform.
          </p>
        </div>

        {/* Tabs */}
        <div style={{ display: "flex", gap: 4, marginBottom: 32, overflowX: "auto", paddingBottom: 4 }}>
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              style={{
                padding: "10px 18px",
                borderRadius: 8,
                border: "1px solid " + (tab === t.id ? "#f59e0b44" : "#27272a"),
                background: tab === t.id ? "#f59e0b12" : "transparent",
                color: tab === t.id ? "#fbbf24" : "#71717a",
                fontSize: 13,
                fontWeight: 600,
                cursor: "pointer",
                whiteSpace: "nowrap",
                transition: "all 0.2s",
              }}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* PHASES */}
        {tab === "phases" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 32 }}>
            {phases.map((phase) => (
              <div key={phase.id} style={{ border: "1px solid #27272a", borderRadius: 16, overflow: "hidden" }}>
                <div style={{ padding: "20px 24px", borderBottom: "1px solid #27272a", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <div style={{ width: 10, height: 10, borderRadius: "50%", background: phase.color }} />
                      <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>{phase.title}</h2>
                      <Badge color={phase.color}>{phase.subtitle}</Badge>
                    </div>
                  </div>
                  <div style={{ background: phase.color + "18", color: phase.color, padding: "6px 16px", borderRadius: 8, fontSize: 14, fontWeight: 700 }}>
                    {phase.revenue}
                  </div>
                </div>
                <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 20 }}>
                  {phase.items.map((item, i) => (
                    <div key={i} style={{ background: "#111116", borderRadius: 12, padding: 20, border: "1px solid #1e1e24" }}>
                      <h3 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 8px 0", color: "#fafafa" }}>{item.name}</h3>
                      <p style={{ fontSize: 14, color: "#a1a1aa", lineHeight: 1.6, margin: "0 0 16px 0" }}>{item.desc}</p>
                      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12 }}>
                        {[
                          { label: "💰 Cena", val: item.price },
                          { label: "🎯 Target", val: item.target },
                          { label: "⏱ Effort", val: item.effort },
                          { label: "🔧 Tech", val: item.tech },
                        ].map((f, j) => (
                          <div key={j} style={{ background: "#0a0a0f", borderRadius: 8, padding: "10px 14px" }}>
                            <div style={{ fontSize: 11, color: "#52525b", fontWeight: 600, marginBottom: 4 }}>{f.label}</div>
                            <div style={{ fontSize: 13, color: "#d4d4d8", lineHeight: 1.5 }}>{f.val}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* QUICK WINS */}
        {tab === "quickwins" && (
          <div>
            <p style={{ fontSize: 14, color: "#a1a1aa", marginBottom: 24, lineHeight: 1.7 }}>
              Konkretne oferty, które możesz wystawić <strong style={{ color: "#fbbf24" }}>jutro</strong> na OLX, Facebooku i LinkedIn. Każda wymaga minimum kodu — bazują na tym co już masz w Broxeen i evo-engine.
            </p>
            <div style={{ display: "grid", gap: 16 }}>
              {quickWins.map((qw, i) => (
                <div key={i} style={{ background: "#111116", border: "1px solid #1e1e24", borderRadius: 14, padding: 20, display: "grid", gridTemplateColumns: "1fr auto", gap: 16, alignItems: "start" }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
                      <span style={{ fontSize: 18 }}>{qw.what.split(" ")[0]}</span>
                      <h3 style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>{qw.what.substring(qw.what.indexOf(" ") + 1)}</h3>
                    </div>
                    <p style={{ fontSize: 13, color: "#a1a1aa", margin: "0 0 10px 0", lineHeight: 1.6 }}>{qw.desc}</p>
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                      <Badge color="#22c55e">🎯 {qw.who}</Badge>
                      <Badge color="#71717a">⏱ {qw.time}</Badge>
                    </div>
                  </div>
                  <div style={{ textAlign: "right", minWidth: 120 }}>
                    <div style={{ fontSize: 20, fontWeight: 800, color: "#fbbf24" }}>{qw.price}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* PREMIUM SKILLS */}
        {tab === "skills" && (
          <div>
            <p style={{ fontSize: 14, color: "#a1a1aa", marginBottom: 24, lineHeight: 1.7 }}>
              Skills do sprzedaży w marketplace. <strong style={{ color: "#fbbf24" }}>Jednorazowy zakup</strong> (licencja perpetual) lub <strong style={{ color: "#22c55e" }}>w pakiecie All-Access (149 PLN/mies.)</strong>.
              Wiele z tych skilli już istnieje w evo-engine — potrzebują tylko opakowania i dokumentacji.
            </p>
            <div style={{ border: "1px solid #27272a", borderRadius: 12, overflow: "hidden" }}>
              <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 80px 80px 2fr", padding: "12px 20px", background: "#18181b", fontSize: 11, fontWeight: 700, color: "#52525b", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                <span>Skill</span>
                <span>Kategoria</span>
                <span>Cena</span>
                <span>Popyt</span>
                <span>Opis</span>
              </div>
              {premiumSkills.map((s, i) => (
                <div key={i} style={{ display: "grid", gridTemplateColumns: "2fr 1fr 80px 80px 2fr", padding: "14px 20px", borderTop: "1px solid #1e1e24", fontSize: 13, alignItems: "center" }}>
                  <span style={{ fontWeight: 600, color: "#fafafa", fontFamily: "monospace", fontSize: 12 }}>{s.name}</span>
                  <Badge color="#6366f1">{s.cat}</Badge>
                  <span style={{ fontWeight: 700, color: "#fbbf24" }}>{s.price}</span>
                  <span>{s.demand}</span>
                  <span style={{ color: "#a1a1aa" }}>{s.desc}</span>
                </div>
              ))}
            </div>
            <div style={{ marginTop: 20, padding: 20, background: "#111116", borderRadius: 12, border: "1px solid #1e1e24" }}>
              <h4 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 8px 0", color: "#fbbf24" }}>💡 Model licencjonowania</h4>
              <div style={{ fontSize: 13, color: "#a1a1aa", lineHeight: 1.7 }}>
                <strong style={{ color: "#d4d4d8" }}>Opcja A — Jednorazowy zakup:</strong> Klient kupuje .zip ze skillem, może modyfikować, brak updates. Najszybszy cash flow.<br />
                <strong style={{ color: "#d4d4d8" }}>Opcja B — Licencja per seat:</strong> 29 PLN/mies. per skill, zawiera updates + support. Lepszy LTV.<br />
                <strong style={{ color: "#d4d4d8" }}>Opcja C — All-Access Bundle:</strong> 149 PLN/mies. = wszystkie premium skills + priorytetowy support. Najwyższy ARPU.<br />
                <strong style={{ color: "#d4d4d8" }}>Rekomendacja:</strong> Start z Opcją A (instant revenue) + Opcja C dla power users. Dodaj B w fazie skalowania.
              </div>
            </div>
          </div>
        )}

        {/* CHANNELS */}
        {tab === "channels" && (
          <div>
            <p style={{ fontSize: 14, color: "#a1a1aa", marginBottom: 24, lineHeight: 1.7 }}>
              Kanały sprzedaży posortowane od <strong style={{ color: "#ef4444" }}>najszybszych</strong> do <strong style={{ color: "#22c55e" }}>najskalowalniejszych</strong>. Zacznij od góry.
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {channels.map((ch, i) => (
                <div key={i} style={{ background: "#111116", border: "1px solid #1e1e24", borderRadius: 12, padding: "18px 20px", display: "grid", gridTemplateColumns: "180px 90px 100px 1fr", gap: 16, alignItems: "center" }}>
                  <div style={{ fontWeight: 700, fontSize: 14 }}>{ch.ch}</div>
                  <div style={{ fontSize: 12, color: "#22c55e", fontWeight: 600 }}>{ch.cost}</div>
                  <Badge color="#f59e0b">{ch.reach}</Badge>
                  <div style={{ fontSize: 13, color: "#a1a1aa" }}>{ch.desc}</div>
                </div>
              ))}
            </div>
            <div style={{ marginTop: 24, padding: 20, background: "#18181b", borderRadius: 12, border: "1px solid #f59e0b33" }}>
              <h4 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px 0", color: "#fbbf24" }}>🇵🇱 Grupy Facebook do targetowania (Polska)</h4>
              <div style={{ fontSize: 13, color: "#a1a1aa", lineHeight: 2 }}>
                "Programowanie — Pair Programming PL" (45K) · "Startups Poland" (12K) · "Python Polska" (18K) · "E-commerce Polska — Sklepy Internetowe" (38K) · "Małe firmy — Marketing" (65K) · "Automatyzacja IT" (8K) · "DevOps Polska" (6K) · "Monitoring i CCTV Polska" (15K) · "Freelancerzy IT Polska" (22K)
              </div>
            </div>
          </div>
        )}

        {/* TECH STACK */}
        {tab === "tech" && (
          <div>
            <p style={{ fontSize: 14, color: "#a1a1aa", marginBottom: 24, lineHeight: 1.7 }}>
              Minimalistyczny stack na szybki start. Zasada: <strong style={{ color: "#fbbf24" }}>używaj tego co masz</strong>, nie buduj nowego.
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {techStack.map((ts, i) => (
                <div key={i} style={{ background: "#111116", border: "1px solid #1e1e24", borderRadius: 12, padding: 20 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                    <h3 style={{ fontSize: 14, fontWeight: 700, margin: 0, color: "#fafafa" }}>{ts.layer}</h3>
                    <span style={{ fontSize: 13, fontWeight: 600, color: "#fbbf24", fontFamily: "monospace" }}>{ts.rec}</span>
                  </div>
                  <p style={{ fontSize: 13, color: "#a1a1aa", margin: 0, lineHeight: 1.6 }}>{ts.reason}</p>
                </div>
              ))}
            </div>

            <div style={{ marginTop: 32, padding: 24, background: "linear-gradient(135deg, #111116, #18181b)", borderRadius: 16, border: "1px solid #27272a" }}>
              <h3 style={{ fontSize: 18, fontWeight: 800, margin: "0 0 16px 0", color: "#fafafa" }}>🏁 Plan działania — pierwsze 7 dni</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {[
                  { day: "Dzień 1", task: "Landing page na Carrd.co z 3 ofertami (audit sieci, bot monitoringu cen, LLM proxy). Stripe payment links." },
                  { day: "Dzień 2", task: "Opublikuj na OLX (3 ogłoszenia: automatyzacja, monitoring kamer, audyt IT). Wstaw na 2–3 grupy FB." },
                  { day: "Dzień 3", task: "Nagraj 2-min demo video Broxeen (skan sieci + wykrycie kamery). Upload na YouTube i LinkedIn." },
                  { day: "Dzień 4", task: "Postaw LiteLLM proxy na Hetzner VPS (€4.5/mies.). Podepnij Stripe metered billing." },
                  { day: "Dzień 5", task: "Opakuj 3 premium skille (browser_automation, network_scanner, web_scraper) — README + manifest + .zip do pobrania." },
                  { day: "Dzień 6", task: "Gig na Fiverr: 'Custom AI automation bot — network monitoring, web scraping, form filling'." },
                  { day: "Dzień 7", task: "Post na LinkedIn PL + cold DM do 10 małych firm: 'Darmowy audyt sieci — zajmie 15 min, dostaniesz raport PDF'." },
                ].map((d, i) => (
                  <div key={i} style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>
                    <div style={{ minWidth: 70, fontSize: 12, fontWeight: 700, color: "#f59e0b", paddingTop: 2 }}>{d.day}</div>
                    <div style={{ fontSize: 13, color: "#d4d4d8", lineHeight: 1.6 }}>{d.task}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        <div style={{ marginTop: 48, padding: 24, borderTop: "1px solid #1e1e24", fontSize: 12, color: "#52525b", textAlign: "center" }}>
          evo-engine + Broxeen GTM Strategy · Marzec 2026 · Tom Sapletta
        </div>
      </div>
    </div>
  );
}
