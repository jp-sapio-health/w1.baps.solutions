import { type CSSProperties, type ReactNode, useEffect, useRef, useState } from "react";
import { Badge, Button, useToast } from "@pikoloo/darwin-ui";
import readmeRaw from "../../README.md?raw";

const REPO = "https://github.com/jp-sapio-health/w1.baps.solutions";
const DMG = `${REPO}/releases/latest/download/W1.dmg`;

/* ---------------------------------------------------------------- navbar */

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
          <a href="#readme">Docs</a>
          <a href={REPO} target="_blank" rel="noreferrer">
            GitHub
          </a>
        </nav>
      </header>
    </div>
  );
}

/* ------------------------------------------------------- hero: live pill */

const DEMO_TEXT = "jay svāminārāyan, āje kathā sāras hatī.";

/** The app's floating widget, working: hold it (or hold Option) to "listen", release to type. */
function PillDemo() {
  const [state, setState] = useState<"idle" | "listening" | "typing" | "done">("idle");
  const [typed, setTyped] = useState("");
  const timers = useRef<number[]>([]);

  const clearTimers = () => {
    timers.current.forEach((t) => window.clearTimeout(t));
    timers.current = [];
  };

  const start = () => {
    if (state === "listening") return;
    clearTimers();
    setTyped("");
    setState("listening");
  };

  const stop = () => {
    if (state !== "listening") return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) {
      setTyped(DEMO_TEXT);
      setState("done");
      return;
    }
    setState("typing");
    DEMO_TEXT.split("").forEach((_, i) => {
      timers.current.push(
        window.setTimeout(() => {
          setTyped(DEMO_TEXT.slice(0, i + 1));
          if (i === DEMO_TEXT.length - 1) setState("done");
        }, 240 + i * 22),
      );
    });
  };

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "Alt") start();
    };
    const up = (e: KeyboardEvent) => {
      if (e.key === "Alt") stop();
    };
    window.addEventListener("keydown", down);
    window.addEventListener("keyup", up);
    return () => {
      window.removeEventListener("keydown", down);
      window.removeEventListener("keyup", up);
      clearTimers();
    };
  });

  return (
    <div className="demo">
      <div className="demo-field" aria-live="polite">
        {typed ? (
          <span>{typed}</span>
        ) : (
          <span className="demo-placeholder">
            {state === "listening" ? "listening…" : "text lands here"}
          </span>
        )}
        {(state === "typing" || state === "done") && <span className="caret" />}
      </div>
      <button
        type="button"
        className={`pill ${state === "listening" ? "pill-live" : ""}`}
        onPointerDown={start}
        onPointerUp={stop}
        onPointerLeave={stop}
        aria-label="Hold to simulate dictation"
      >
        {state === "listening" ? (
          <span className="wave">
            {Array.from({ length: 9 }, (_, i) => (
              <i key={i} style={{ animationDelay: `${i * 0.09}s` }} />
            ))}
          </span>
        ) : (
          <span className="pill-rest" />
        )}
      </button>
      <p className="demo-hint">
        hold the pill, or hold <kbd>⌥ Option</kbd>
      </p>
    </div>
  );
}

function Hero() {
  return (
    <section className="hero">
      <Badge variant="secondary">macOS · on-device</Badge>
      <p className="hero-spec">whisper-large-v3-turbo | runs on the Apple Silicon GPU</p>
      <PillDemo />
    </section>
  );
}

/* ------------------------------------------------------------ code block */

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

/* ------------------------------------------------------------ bento grid */

function Tile({
  span,
  eyebrow,
  children,
  className = "",
  id,
}: {
  span: string;
  eyebrow?: string;
  children: ReactNode;
  className?: string;
  id?: string;
}) {
  return (
    <div className={`tile ${span} ${className}`} id={id}>
      {eyebrow && <div className="eyebrow">{eyebrow}</div>}
      {children}
    </div>
  );
}

function Bento() {
  return (
    <section className="bento">
      {/* install: the tile the page exists for */}
      <Tile span="s7 tall" eyebrow="install" id="install" className="tile-install">
        <div className="install-actions">
          <Button variant="primary" size="lg" onClick={() => window.open(DMG, "_blank")}>
            Download W1.dmg
          </Button>
          <span className="install-meta">233 MB · drag to Applications · right-click, Open</span>
        </div>
        <div className="install-or">or from source</div>
        <CodeBlock
          title="Terminal"
          lines={[
            "git clone " + REPO + ".git w1",
            "cd w1 && ./install.sh   # uv + venv + model, one time",
            "./w1 app",
          ]}
        />
        <p className="install-perms">
          Grant <strong>Microphone</strong>, <strong>Accessibility</strong> and{" "}
          <strong>Input Monitoring</strong> when asked. The menu bar shows ! until all three are
          on.
        </p>
      </Tile>

      <Tile span="s5" eyebrow="gujarati (katha)">
        <div className="translit">
          <span className="gu">મંદિર કથા ભગવાન</span>
          <span className="arrow">→</span>
          <span className="roman">mandir kathā bhagavān</span>
        </div>
        <p>
          A deterministic transliterator, not a model guess. One diacritic, ā, exactly as the
          sampradāy's publications print it.
        </p>
      </Tile>

      <Tile span="s5" eyebrow="private by construction">
        <h3>The only network call is the one-time model download.</h3>
        <p>
          Audio is held in memory, transcribed on the GPU, discarded. No server, no account, no
          telemetry. Safe for clinical notes.
        </p>
      </Tile>

      <Tile span="s3 center" eyebrow="hotkey">
        <div className="keycap">⌥</div>
        <p className="keycap-label">hold Right-Option</p>
      </Tile>

      <Tile span="s4" eyebrow="four modes">
        <ul className="mode-list">
          <li>
            <strong>Dictate</strong> verbatim, clinical-safe
          </li>
          <li>
            <strong>Default</strong> sacred terms corrected
          </li>
          <li>
            <strong>Clean +</strong> fillers out, tidy prose
          </li>
          <li>
            <strong>Gujarati</strong> ā-only romanisation
          </li>
        </ul>
      </Tile>

      <Tile span="s4" eyebrow="model">
        <h3>whisper-large-v3-turbo</h3>
        <p>
          Distilled by OpenAI from large-v3 (decoder cut 32 layers to 4), converted to MLX,
          float16 on Metal. About 1.5 GB, cached once.
        </p>
      </Tile>

      <Tile span="s4" eyebrow="hallucination gates">
        <h3>
          Silence pastes <span className="reject">nothing</span>.
        </h3>
        <p>
          Known Whisper artifacts are dropped, and low-confidence takes (no_speech &gt; 0.6, logprob
          &lt; -1.0) show a red X instead of inserting noise.
        </p>
      </Tile>

      <Tile span="s6 dark" eyebrow="cli">
        <CodeBlock
          title="w1"
          lines={[
            "./w1 doctor       # deps, model, permissions",
            "./w1 transcribe FILE --mode gujarati",
            "./w1 debug-keys   # watch the hotkey listener",
          ]}
        />
      </Tile>

      <Tile span="s6" eyebrow="open">
        <h3>Small, tested, readable.</h3>
        <p>
          52 unit tests, 96% coverage on the engine, an import-linter contract keeping the core
          free of macOS imports, and a build that refuses to ship a bundle that fails its own
          runtime self-test.
        </p>
        <a className="tile-link" href={REPO} target="_blank" rel="noreferrer">
          Read the source →
        </a>
      </Tile>
    </section>
  );
}

/* ------------------------------------------------- readme, from the repo */

type Block =
  | { kind: "h"; level: number; text: string }
  | { kind: "code"; lines: string[] }
  | { kind: "table"; head: string[]; rows: string[][] }
  | { kind: "list"; ordered: boolean; items: string[] }
  | { kind: "p"; text: string };

function parseMarkdown(src: string): Block[] {
  const lines = src.split("\n");
  const blocks: Block[] = [];
  let i = 0;
  while (i < lines.length) {
    const l = lines[i];
    if (l.startsWith("```")) {
      const code: string[] = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) code.push(lines[i++]);
      i++;
      blocks.push({ kind: "code", lines: code });
    } else if (/^#{1,3} /.test(l)) {
      const level = l.match(/^#+/)![0].length;
      blocks.push({ kind: "h", level, text: l.replace(/^#+ /, "") });
      i++;
    } else if (l.startsWith("|") && lines[i + 1]?.startsWith("|")) {
      const rows: string[][] = [];
      while (i < lines.length && lines[i].startsWith("|")) {
        rows.push(lines[i].split("|").slice(1, -1).map((c) => c.trim()));
        i++;
      }
      blocks.push({ kind: "table", head: rows[0], rows: rows.slice(2) });
    } else if (/^(-|\d+\.) /.test(l)) {
      const ordered = /^\d+\./.test(l);
      const items: string[] = [];
      while (i < lines.length && (/^(-|\d+\.) /.test(lines[i]) || /^ {2,}\S/.test(lines[i]))) {
        if (/^(-|\d+\.) /.test(lines[i])) items.push(lines[i].replace(/^(-|\d+\.) /, ""));
        else items[items.length - 1] += " " + lines[i].trim();
        i++;
      }
      blocks.push({ kind: "list", ordered, items });
    } else if (l.trim() === "") {
      i++;
    } else {
      const para: string[] = [];
      while (i < lines.length && lines[i].trim() !== "" && !/^(#|```|\||-|\d+\.)/.test(lines[i]))
        para.push(lines[i++]);
      blocks.push({ kind: "p", text: para.join(" ") });
    }
  }
  return blocks;
}

/** Inline markdown: `code`, **bold**, [text](url). Small on purpose. */
function Inline({ text }: { text: string }) {
  const parts = text.split(/(`[^`]+`|\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\))/g);
  return (
    <>
      {parts.map((p, i) => {
        if (p.startsWith("`")) return <code key={i}>{p.slice(1, -1)}</code>;
        if (p.startsWith("**")) return <strong key={i}>{p.slice(2, -2)}</strong>;
        const link = p.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
        if (link)
          return (
            <a key={i} href={link[2]} target="_blank" rel="noreferrer">
              {link[1]}
            </a>
          );
        return <span key={i}>{p}</span>;
      })}
    </>
  );
}

function Readme() {
  const blocks = parseMarkdown(readmeRaw);
  return (
    <section className="readme" id="readme">
      <div className="eyebrow">README.md · rendered from the repo</div>
      {blocks.map((b, i) => {
        switch (b.kind) {
          case "h": {
            if (b.level === 1) return null; /* the page already says W1 */
            const H = b.level === 2 ? "h2" : "h3";
            return <H key={i}>{b.text}</H>;
          }
          case "code":
            return <CodeBlock key={i} lines={b.lines} />;
          case "table":
            return (
              <table key={i}>
                <thead>
                  <tr>
                    {b.head.map((h, j) => (
                      <th key={j}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {b.rows.map((r, j) => (
                    <tr key={j}>
                      {r.map((c, k) => (
                        <td key={k}>
                          <Inline text={c} />
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            );
          case "list": {
            const L = b.ordered ? "ol" : "ul";
            return (
              <L key={i}>
                {b.items.map((it, j) => (
                  <li key={j}>
                    <Inline text={it} />
                  </li>
                ))}
              </L>
            );
          }
          default:
            return (
              <p key={i}>
                <Inline text={b.text} />
              </p>
            );
        }
      })}
    </section>
  );
}

/* ------------------------------------------------------------------ page */

export function App() {
  return (
    <div className="page light" id="top">
      <Navbar />
      <Hero />
      <Bento />
      <Readme />
      <footer>
        <span className="foot-brand">
          <img src="/baps-logo.svg" alt="BAPS" width={18} height={18} />
          W1
        </span>
        <a href={REPO} target="_blank" rel="noreferrer">
          GitHub
        </a>
      </footer>
    </div>
  );
}
