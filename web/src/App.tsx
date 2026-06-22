import { useState } from "react";
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
  const toast = useToast();
  return (
    <section className="hero">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
      >
        <div className="wordmark">
          <span className="devanagari">वाणी</span>
          <span className="dot">·</span>
          <span className="w1">W1</span>
          <Badge variant="success">v1.1</Badge>
        </div>
        <h1>Local, private dictation.</h1>
        <p className="lede">
          Press a key, speak, it types. Whisper runs <strong>entirely on your Mac</strong> via Apple
          MLX — no cloud, no account, no subscription. English and BAPS Gujarati sacred terms,
          fully on-device.
        </p>
        <div className="cta">
          <Button
            variant="primary"
            size="lg"
            onClick={() =>
              toast.showToast("Grab the latest W1.dmg from the repo's Releases.", {
                title: "Download W1",
                type: "success",
              })
            }
          >
            Download for macOS
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
    <section className="modes">
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

function HowItWorks() {
  return (
    <section className="how">
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
    <div className="page light">
      <Hero />
      <ControlPanel />
      <Modes />
      <HowItWorks />
      <footer>
        <span>वाणी · W1</span>
        <span className="muted">Built for sewa. Private by design.</span>
        <a href={REPO} target="_blank" rel="noreferrer">
          GitHub
        </a>
      </footer>
    </div>
  );
}
