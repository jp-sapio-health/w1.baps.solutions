import { type CSSProperties, useState } from "react";
import { motion } from "framer-motion";
import {
  Window,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  Button,
  Badge,
  Switch,
  Select,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  TableHeaderCell,
  useToast,
} from "@pikoloo/darwin-ui";

const REPO = "https://github.com/jp-sapio-health/w1.baps.solutions";

// Floating glass navbar — the chrome recipe from the Sapio docs design system (sticky, max-w-4xl,
// translucent glass pill), with the BAPS logo + W1 wordmark in place of the Sapio mark.
const GLASS_NAV: CSSProperties = {
  background: "rgba(255,255,255,0.5)",
  backdropFilter: "blur(24px) saturate(1.8)",
  WebkitBackdropFilter: "blur(24px) saturate(1.8)",
  border: "1px solid rgba(255,255,255,0.6)",
  boxShadow:
    "0 1px 3px rgba(0,0,0,0.04), 0 8px 24px rgba(0,0,0,0.06), inset 0 1px 0 rgba(255,255,255,0.7)",
};

function Navbar() {
  return (
    <div className="nav-outer">
      <header className="nav-pill" style={GLASS_NAV}>
        <a className="nav-brand" href="#top">
          <img src="/baps-logo.svg" alt="BAPS" width={22} height={22} />
          <span className="nav-word">
            <strong>W1</strong>
            <span className="nav-sub">.baps.solutions</span>
          </span>
        </a>
        <nav className="nav-links">
          <a href="#install">Install</a>
          <a href="#modes">Modes</a>
          <a href="#how">How it works</a>
          <a href={REPO} target="_blank" rel="noreferrer">
            GitHub
          </a>
        </nav>
      </header>
    </div>
  );
}

const MODES = [
  {
    name: "Dictate",
    badge: "verbatim",
    variant: "secondary" as const,
    desc: "Exactly what you said — no terminology changes. The clinical-safe default.",
  },
  {
    name: "Default",
    badge: "sacred-aware",
    variant: "primary" as const,
    desc: "Corrects BAPS Gujarati sacred terms to their canonical spelling, leaving ordinary English untouched.",
  },
  {
    name: "Clean +",
    badge: "editorial",
    variant: "info" as const,
    desc: "Default, plus a light tidy-up — filler removal, place and date casing.",
  },
  {
    name: "Gujarati (katha)",
    badge: "ā-only Roman",
    variant: "accent" as const,
    desc: "Transcribes spoken Gujarati and outputs Roman transliteration with the ā-only diacritic rule.",
  },
];

const STEPS = [
  { n: "1", t: "Hold Right-Option", d: "Press and speak. A floating pill shows a live waveform." },
  { n: "2", t: "Whisper, on-device", d: "Apple MLX runs Whisper locally. No audio ever leaves your Mac." },
  { n: "3", t: "It types", d: "Corrected text is pasted into whatever app is focused." },
];

const HISTORY = [
  { time: "09:41", mode: "Default", text: "We did darshan at the mandir this morning." },
  { time: "09:38", mode: "Dictate", text: "Patient reports intermittent chest pain on exertion." },
  { time: "09:32", mode: "Gujarati", text: "jay svāminārāyan, āje kathā sāras hatī." },
  { time: "09:20", mode: "Clean +", text: "The meeting is on the fourteenth of July in London." },
];

function Hero() {
  const scrollToInstall = () =>
    document.getElementById("install")?.scrollIntoView({ behavior: "smooth" });
  return (
    <section className="hero">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
      >
        <div className="wordmark">
          <Badge variant="secondary">On-device · macOS · v1.1</Badge>
        </div>
        <h1>Local, private dictation.</h1>
        <p className="lede">
          Press a key, speak, it types. Whisper runs <strong>entirely on your Mac</strong> via Apple
          MLX — no cloud, no account, no subscription.
        </p>
        <div className="cta">
          <Button variant="primary" size="lg" onClick={scrollToInstall}>
            Install
          </Button>
          <Button variant="outline" size="lg" onClick={() => window.open(REPO, "_blank")}>
            View source
          </Button>
        </div>
        <p className="privacy-note">🔒 Nothing — no audio, no text — ever leaves your computer.</p>
      </motion.div>
    </section>
  );
}

function ControlPanel() {
  const [tab, setTab] = useState("settings");
  const [mode, setMode] = useState("dictation");
  const [confidence, setConfidence] = useState(true);
  const [panel, setPanel] = useState(true);

  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.3 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="panel-wrap"
    >
      <Window title="W1">
        <Tabs value={tab} onValueChange={setTab} className="panel-tabs">
          <TabsList>
            <TabsTrigger value="settings">Settings</TabsTrigger>
            <TabsTrigger value="history">History</TabsTrigger>
            <TabsTrigger value="about">About</TabsTrigger>
          </TabsList>

          <TabsContent value="settings">
            <div className="settings-grid">
              <label className="field">
                <span>Correction mode</span>
                <Select
                  value={mode}
                  onChange={(e) => setMode(e.target.value)}
                  options={[
                    { value: "raw", label: "Dictate — verbatim" },
                    { value: "dictation", label: "Default — sacred-aware" },
                    { value: "document", label: "Clean + — editorial" },
                    { value: "gujarati", label: "Gujarati (katha)" },
                  ]}
                />
              </label>
              <div className="field">
                <span>Hotkey</span>
                <kbd>Hold Right-Option</kbd>
              </div>
              <Switch
                label="Confidence gate — never paste low-confidence audio"
                checked={confidence}
                onChange={setConfidence}
              />
              <Switch
                label="Floating paste panel when no field is focused (⌘⇧V)"
                checked={panel}
                onChange={setPanel}
              />
            </div>
          </TabsContent>

          <TabsContent value="history">
            <Table>
              <TableHead>
                <TableRow>
                  <TableHeaderCell>Time</TableHeaderCell>
                  <TableHeaderCell>Mode</TableHeaderCell>
                  <TableHeaderCell>Transcript</TableHeaderCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {HISTORY.map((h) => (
                  <TableRow key={h.time}>
                    <TableCell>{h.time}</TableCell>
                    <TableCell>
                      <Badge variant="secondary">{h.mode}</Badge>
                    </TableCell>
                    <TableCell>{h.text}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TabsContent>

          <TabsContent value="about">
            <div className="about">
              <p>
                <strong>W1 v1.1</strong> — a local, privacy-first macOS dictation app that replaces
                paid tools like Wispr Flow, and knows BAPS Gujarati sacred terminology.
              </p>
              <p className="muted">Built for sewa. Private by design.</p>
            </div>
          </TabsContent>
        </Tabs>
      </Window>
    </motion.div>
  );
}

function Modes() {
  return (
    <section className="modes" id="modes">
      <h2>Four modes, one keypress</h2>
      <div className="mode-grid">
        {MODES.map((m, i) => (
          <motion.div
            key={m.name}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.4 }}
            transition={{ duration: 0.4, ease: "easeOut", delay: i * 0.06 }}
          >
            <Card>
              <CardHeader>
                <CardTitle>
                  {m.name} <Badge variant={m.variant}>{m.badge}</Badge>
                </CardTitle>
                <CardDescription>{m.desc}</CardDescription>
              </CardHeader>
            </Card>
          </motion.div>
        ))}
      </div>
    </section>
  );
}

function CodeBlock({ title, lines }: { title?: string; lines: string[] }) {
  const toast = useToast();
  const copy = () => {
    navigator.clipboard?.writeText(lines.join("\n"));
    toast.showToast("Copied to clipboard", { type: "success" });
  };
  return (
    <div className="codeblock">
      <div className="codeblock-bar">
        <span className="dot r" />
        <span className="dot y" />
        <span className="dot g" />
        {title && <span className="codeblock-title">{title}</span>}
        <button className="codeblock-copy" onClick={copy}>
          Copy
        </button>
      </div>
      <pre className="codeblock-body">
        {lines.map((l, i) => {
          const h = l.indexOf("#");
          if (h > 0)
            return (
              <code key={i}>
                {l.slice(0, h)}
                <span className="comment">{l.slice(h)}</span>
              </code>
            );
          return (
            <code key={i} className={l.startsWith("#") ? "comment" : ""}>
              {l || " "}
            </code>
          );
        })}
      </pre>
    </div>
  );
}

function Install() {
  return (
    <section className="install" id="install">
      <h2>Install</h2>
      <p className="section-lede">
        Apple Silicon Mac with{" "}
        <a href="https://docs.astral.sh/uv/" target="_blank" rel="noreferrer">
          uv
        </a>{" "}
        installed. One command sets up the virtualenv, dependencies, and the Whisper model.
      </p>
      <CodeBlock
        title="Terminal"
        lines={[
          "git clone https://github.com/jp-sapio-health/w1.baps.solutions.git w1",
          "cd w1",
          "./install.sh        # venv + deps + model + permission links",
          "./w1 app            # launch the menu-bar app",
        ]}
      />
      <p className="install-note">
        Grant <strong>Microphone</strong>, <strong>Accessibility</strong>, and{" "}
        <strong>Input Monitoring</strong> to your terminal when prompted, then hold{" "}
        <kbd>Right-Option</kbd> and speak.
      </p>
    </section>
  );
}

function Cli() {
  return (
    <section className="cli" id="cli">
      <h2>Command line</h2>
      <CodeBlock
        title="w1"
        lines={[
          "./w1 app                       # menu-bar app + floating widget",
          "./w1 dictate                   # record, correct, paste",
          "./w1 transcribe FILE --mode …  # transcribe an audio file",
          './w1 correct "text" --mode …   # run the correction engine only',
          "./w1 doctor                    # check deps, model, permissions",
        ]}
      />
    </section>
  );
}

function HowItWorks() {
  return (
    <section className="how" id="how">
      <h2>How it works</h2>
      <div className="steps">
        {STEPS.map((s) => (
          <Card key={s.n}>
            <CardContent>
              <div className="step-n">{s.n}</div>
              <h3>{s.t}</h3>
              <p>{s.d}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}

export function App() {
  return (
    <div className="page light" id="top">
      <Navbar />
      <Hero />
      <Install />
      <ControlPanel />
      <Modes />
      <Cli />
      <HowItWorks />
      <footer>
        <span className="foot-brand">
          <img src="/baps-logo.svg" alt="BAPS" width={18} height={18} />
          W1
        </span>
        <span className="muted">Built for sewa. Private by design.</span>
        <a href={REPO} target="_blank" rel="noreferrer">
          GitHub
        </a>
      </footer>
    </div>
  );
}
