import { useState, useRef, useEffect, useCallback } from "react";
import { Mic, MicOff, Activity, Music, BarChart3, Volume2, Settings, Square } from "lucide-react";

// ─── 음악 상수 ───────────────────────────────────────────
const NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
const A4_FREQ = 440;
const A4_MIDI = 69;

// Hz → 음악 노트 변환
function frequencyToNote(freq) {
  if (freq <= 0) return null;
  const midi = 12 * Math.log2(freq / A4_FREQ) + A4_MIDI;
  const rounded = Math.round(midi);
  const name = NOTE_NAMES[((rounded % 12) + 12) % 12];
  const octave = Math.floor(rounded / 12) - 1;
  const cents = Math.round((midi - rounded) * 100);
  return { name, octave, cents, midi: rounded, fullName: `${name}${octave}` };
}

// ─── Autocorrelation 피치 감지 ───────────────────────────
function detectPitch(buffer, sampleRate) {
  const SIZE = buffer.length;

  // RMS 기반 무음 감지
  let rms = 0;
  for (let i = 0; i < SIZE; i++) rms += buffer[i] * buffer[i];
  rms = Math.sqrt(rms / SIZE);
  if (rms < 0.01) return { freq: -1, clarity: 0 };

  // 신호 양 끝의 무음 트리밍
  let start = 0;
  let end = SIZE - 1;
  const threshold = 0.2;
  for (let i = 0; i < SIZE / 2; i++) {
    if (Math.abs(buffer[i]) > threshold) { start = i; break; }
  }
  for (let i = SIZE - 1; i >= SIZE / 2; i--) {
    if (Math.abs(buffer[i]) > threshold) { end = i; break; }
  }
  const trimmed = buffer.slice(start, end + 1);
  const len = trimmed.length;

  // Autocorrelation 계산
  const corr = new Float32Array(len);
  for (let lag = 0; lag < len; lag++) {
    let sum = 0;
    for (let i = 0; i < len - lag; i++) sum += trimmed[i] * trimmed[i + lag];
    corr[lag] = sum;
  }

  // 첫 번째 딥(dip) 이후의 피크 탐색
  let foundDip = false;
  let maxVal = -1;
  let maxIdx = -1;
  const minLag = Math.floor(sampleRate / 1100);
  const maxLag = Math.floor(sampleRate / 60);

  for (let i = Math.max(1, minLag); i < Math.min(len, maxLag); i++) {
    if (!foundDip && corr[i] < corr[i - 1]) foundDip = true;
    if (foundDip && corr[i] > maxVal) {
      maxVal = corr[i];
      maxIdx = i;
    }
  }

  if (maxIdx === -1 || corr[0] === 0) return { freq: -1, clarity: 0 };

  // 파라볼릭 보간
  let shift = 0;
  if (maxIdx > 0 && maxIdx < len - 1) {
    const y1 = corr[maxIdx - 1];
    const y2 = corr[maxIdx];
    const y3 = corr[maxIdx + 1];
    const denom = 2 * (2 * y2 - y1 - y3);
    if (denom !== 0) shift = (y3 - y1) / denom;
  }

  const clarity = maxVal / corr[0];
  const period = maxIdx + shift;
  const freq = sampleRate / period;

  return { freq, clarity };
}

// ─── 피치 → 색상 매핑 ───────────────────────────────────
function noteToColor(noteName) {
  const colors = {
    C: "#ef4444", "C#": "#f97316", D: "#eab308", "D#": "#84cc16",
    E: "#22c55e", F: "#14b8a6", "F#": "#06b6d4", G: "#3b82f6",
    "G#": "#6366f1", A: "#8b5cf6", "A#": "#a855f7", B: "#ec4899",
  };
  return colors[noteName] || "#6b7280";
}

// ─── 센트 바 컴포넌트 ────────────────────────────────────
function CentsBar({ cents }) {
  const offset = Math.max(-50, Math.min(50, cents));
  const pct = ((offset + 50) / 100) * 100;
  const inTune = Math.abs(offset) < 10;
  return (
    <div className="w-full max-w-xs mx-auto mt-2">
      <div className="relative h-3 bg-gray-700 rounded-full overflow-hidden">
        <div className="absolute left-1/2 top-0 w-0.5 h-full bg-gray-500 -translate-x-1/2" />
        <div
          className="absolute top-0.5 h-2 w-3 rounded-full transition-all duration-100"
          style={{
            left: `calc(${pct}% - 6px)`,
            backgroundColor: inTune ? "#22c55e" : Math.abs(offset) < 25 ? "#eab308" : "#ef4444",
          }}
        />
      </div>
      <div className="flex justify-between text-xs text-gray-500 mt-1">
        <span>-50¢</span>
        <span className={inTune ? "text-green-400 font-bold" : "text-gray-400"}>
          {offset > 0 ? "+" : ""}{offset}¢
        </span>
        <span>+50¢</span>
      </div>
    </div>
  );
}

// ─── Waveform Canvas ─────────────────────────────────────
function WaveformCanvas({ analyser, isActive }) {
  const canvasRef = useRef(null);
  const animRef = useRef(null);

  useEffect(() => {
    if (!analyser || !isActive) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    const bufferLength = analyser.fftSize;
    const dataArray = new Float32Array(bufferLength);

    const draw = () => {
      animRef.current = requestAnimationFrame(draw);
      analyser.getFloatTimeDomainData(dataArray);

      const w = canvas.width;
      const h = canvas.height;
      ctx.fillStyle = "#111827";
      ctx.fillRect(0, 0, w, h);

      ctx.strokeStyle = "#1f2937";
      ctx.lineWidth = 1;
      for (let y = 0; y < h; y += h / 4) {
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
      }

      ctx.strokeStyle = "#374151";
      ctx.beginPath(); ctx.moveTo(0, h / 2); ctx.lineTo(w, h / 2); ctx.stroke();

      const gradient = ctx.createLinearGradient(0, 0, w, 0);
      gradient.addColorStop(0, "#3b82f6");
      gradient.addColorStop(0.5, "#8b5cf6");
      gradient.addColorStop(1, "#06b6d4");
      ctx.strokeStyle = gradient;
      ctx.lineWidth = 2;
      ctx.beginPath();

      const sliceWidth = w / bufferLength;
      let x = 0;
      for (let i = 0; i < bufferLength; i++) {
        const v = dataArray[i];
        const y = (v * 0.5 + 0.5) * h;
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        x += sliceWidth;
      }
      ctx.stroke();

      ctx.strokeStyle = gradient;
      ctx.lineWidth = 1;
      ctx.globalAlpha = 0.3;
      ctx.stroke();
      ctx.globalAlpha = 1;
    };
    draw();
    return () => { if (animRef.current) cancelAnimationFrame(animRef.current); };
  }, [analyser, isActive]);

  return (
    <canvas
      ref={canvasRef}
      width={800}
      height={150}
      className="w-full h-32 sm:h-40 rounded-lg border border-gray-700/50"
    />
  );
}

// ─── 피치 히스토리 그래프 Canvas ─────────────────────────
function PitchHistoryCanvas({ history }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;
    const pad = { top: 25, bottom: 30, left: 50, right: 20 };
    const plotW = w - pad.left - pad.right;
    const plotH = h - pad.top - pad.bottom;

    ctx.fillStyle = "#111827";
    ctx.fillRect(0, 0, w, h);

    if (history.length < 2) {
      ctx.fillStyle = "#6b7280";
      ctx.font = "14px monospace";
      ctx.textAlign = "center";
      ctx.fillText("Sing to see pitch history", w / 2, h / 2);
      return;
    }

    const midiValues = history.map((d) => d.midi).filter((m) => m > 0);
    const minMidi = Math.max(36, Math.min(...midiValues) - 3);
    const maxMidi = Math.min(96, Math.max(...midiValues) + 3);
    const midiRange = maxMidi - minMidi || 1;

    const toX = (i) => pad.left + (i / (history.length - 1)) * plotW;
    const toY = (midi) => pad.top + plotH - ((midi - minMidi) / midiRange) * plotH;

    ctx.textAlign = "right";
    ctx.font = "11px monospace";
    for (let m = Math.ceil(minMidi / 12) * 12; m <= maxMidi; m += 12) {
      const y = toY(m);
      ctx.strokeStyle = "#1f2937";
      ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(w - pad.right, y); ctx.stroke();
      const note = NOTE_NAMES[m % 12] + (Math.floor(m / 12) - 1);
      ctx.fillStyle = "#9ca3af";
      ctx.fillText(note, pad.left - 8, y + 4);
    }
    for (let m = minMidi; m <= maxMidi; m++) {
      const y = toY(m);
      ctx.strokeStyle = "#111d2e";
      ctx.lineWidth = 0.5;
      ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(w - pad.right, y); ctx.stroke();
    }

    const gradient = ctx.createLinearGradient(pad.left, 0, w - pad.right, 0);
    gradient.addColorStop(0, "#6366f1");
    gradient.addColorStop(0.5, "#8b5cf6");
    gradient.addColorStop(1, "#a855f7");

    ctx.strokeStyle = gradient;
    ctx.lineWidth = 2.5;
    ctx.lineJoin = "round";
    ctx.beginPath();
    let started = false;
    for (let i = 0; i < history.length; i++) {
      if (history[i].midi <= 0) { started = false; continue; }
      const x = toX(i);
      const y = toY(history[i].midi);
      if (!started) { ctx.moveTo(x, y); started = true; }
      else ctx.lineTo(x, y);
    }
    ctx.stroke();

    const step = Math.max(1, Math.floor(history.length / 80));
    for (let i = 0; i < history.length; i += step) {
      if (history[i].midi <= 0) continue;
      const x = toX(i);
      const y = toY(history[i].midi);
      ctx.fillStyle = noteToColor(history[i].name);
      ctx.beginPath(); ctx.arc(x, y, 3, 0, Math.PI * 2); ctx.fill();
    }

    ctx.fillStyle = "#6b7280";
    ctx.font = "10px monospace";
    ctx.textAlign = "center";
    const totalSec = history.length * 0.05;
    for (let t = 0; t <= totalSec; t += Math.max(1, Math.round(totalSec / 6))) {
      const idx = Math.round((t / totalSec) * (history.length - 1));
      if (idx < history.length) {
        ctx.fillText(`${t.toFixed(0)}s`, toX(idx), h - pad.bottom + 18);
      }
    }

    ctx.fillStyle = "#9ca3af";
    ctx.font = "12px monospace";
    ctx.textAlign = "left";
    ctx.fillText("Pitch History (MIDI)", pad.left, 16);

  }, [history]);

  return (
    <canvas
      ref={canvasRef}
      width={800}
      height={220}
      className="w-full h-44 sm:h-56 rounded-lg border border-gray-700/50"
    />
  );
}

// ═══════════════════════════════════════════════════════════
// ─── 메인 앱 ─────────────────────────────────────────────
// ═══════════════════════════════════════════════════════════
export default function App() {
  const [isActive, setIsActive] = useState(false);
  const [currentNote, setCurrentNote] = useState(null);
  const [currentFreq, setCurrentFreq] = useState(0);
  const [currentClarity, setCurrentClarity] = useState(0);
  const [pitchHistory, setPitchHistory] = useState([]);
  const [gain, setGain] = useState(1.0);
  const [hpfFreq, setHpfFreq] = useState(85);
  const [showSettings, setShowSettings] = useState(false);
  const [rmsLevel, setRmsLevel] = useState(0);

  const audioCtxRef = useRef(null);
  const analyserRef = useRef(null);
  const gainNodeRef = useRef(null);
  const hpfNodeRef = useRef(null);
  const sourceRef = useRef(null);
  const streamRef = useRef(null);
  const animFrameRef = useRef(null);
  const historyRef = useRef([]);

  const analyse = useCallback(() => {
    if (!analyserRef.current) return;

    const analyser = analyserRef.current;
    const bufferLength = analyser.fftSize;
    const buffer = new Float32Array(bufferLength);
    analyser.getFloatTimeDomainData(buffer);

    let rms = 0;
    for (let i = 0; i < bufferLength; i++) rms += buffer[i] * buffer[i];
    rms = Math.sqrt(rms / bufferLength);
    setRmsLevel(Math.min(1, rms * 5));

    const { freq, clarity } = detectPitch(buffer, audioCtxRef.current.sampleRate);

    if (freq > 60 && freq < 1100 && clarity > 0.9) {
      const note = frequencyToNote(freq);
      setCurrentNote(note);
      setCurrentFreq(freq);
      setCurrentClarity(clarity);
      historyRef.current = [
        ...historyRef.current.slice(-599),
        { midi: note.midi + note.cents / 100, name: note.name },
      ];
    } else {
      historyRef.current = [
        ...historyRef.current.slice(-599),
        { midi: -1, name: "" },
      ];
    }

    setPitchHistory([...historyRef.current]);
    animFrameRef.current = requestAnimationFrame(analyse);
  }, []);

  const startMonitoring = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false,
        },
      });
      streamRef.current = stream;

      const audioCtx = new (window.AudioContext || window.webkitAudioContext)({
        latencyHint: "interactive",
        sampleRate: 44100,
      });
      audioCtxRef.current = audioCtx;

      const source = audioCtx.createMediaStreamSource(stream);
      sourceRef.current = source;

      const hpf = audioCtx.createBiquadFilter();
      hpf.type = "highpass";
      hpf.frequency.value = hpfFreq;
      hpf.Q.value = 0.7;
      hpfNodeRef.current = hpf;

      const gainNode = audioCtx.createGain();
      gainNode.gain.value = gain;
      gainNodeRef.current = gainNode;

      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 2048;
      analyser.smoothingTimeConstant = 0.1;
      analyserRef.current = analyser;

      source.connect(hpf);
      hpf.connect(gainNode);
      gainNode.connect(analyser);

      setIsActive(true);
      historyRef.current = [];
      setPitchHistory([]);
      animFrameRef.current = requestAnimationFrame(analyse);
    } catch (err) {
      console.error("Mic access failed:", err);
      alert("마이크 접근에 실패했습니다. 브라우저 권한을 확인해 주세요.");
    }
  }, [gain, hpfFreq, analyse]);

  const stopMonitoring = useCallback(() => {
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    if (sourceRef.current) sourceRef.current.disconnect();
    if (audioCtxRef.current) audioCtxRef.current.close();
    if (streamRef.current) streamRef.current.getTracks().forEach((t) => t.stop());

    analyserRef.current = null;
    audioCtxRef.current = null;
    sourceRef.current = null;
    streamRef.current = null;

    setIsActive(false);
    setCurrentNote(null);
    setCurrentFreq(0);
    setCurrentClarity(0);
    setRmsLevel(0);
  }, []);

  useEffect(() => {
    if (gainNodeRef.current) gainNodeRef.current.gain.value = gain;
  }, [gain]);
  useEffect(() => {
    if (hpfNodeRef.current) hpfNodeRef.current.frequency.value = hpfFreq;
  }, [hpfFreq]);

  useEffect(() => () => stopMonitoring(), [stopMonitoring]);

  const noteColor = currentNote ? noteToColor(currentNote.name) : "#6b7280";

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col">
      {/* ──── 헤더 ──── */}
      <header className="bg-gray-900/80 backdrop-blur border-b border-gray-800 px-4 py-3 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-2">
          <Music className="w-5 h-5 text-purple-400" />
          <h1 className="text-base sm:text-lg font-bold bg-gradient-to-r from-purple-400 to-cyan-400 bg-clip-text text-transparent">
            Vocal Pitch Analyzer
          </h1>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="p-2 rounded-lg hover:bg-gray-800 transition text-gray-400 hover:text-gray-200"
          >
            <Settings className="w-5 h-5" />
          </button>
          {isActive ? (
            <button
              onClick={stopMonitoring}
              className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg text-sm font-medium transition"
            >
              <Square className="w-4 h-4" />
              <span className="hidden sm:inline">Stop</span>
            </button>
          ) : (
            <button
              onClick={startMonitoring}
              className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg text-sm font-medium transition"
            >
              <Mic className="w-4 h-4" />
              <span className="hidden sm:inline">Start Monitoring</span>
            </button>
          )}
        </div>
      </header>

      {/* ──── 설정 패널 ──── */}
      {showSettings && (
        <div className="bg-gray-900 border-b border-gray-800 px-4 py-4">
          <div className="max-w-3xl mx-auto grid grid-cols-1 sm:grid-cols-2 gap-4">
            <label className="block">
              <span className="text-xs text-gray-400 mb-1 block">
                Input Gain: {gain.toFixed(1)}x
              </span>
              <input
                type="range" min="0.1" max="5" step="0.1" value={gain}
                onChange={(e) => setGain(parseFloat(e.target.value))}
                className="w-full accent-purple-500"
              />
            </label>
            <label className="block">
              <span className="text-xs text-gray-400 mb-1 block">
                High-pass Filter: {hpfFreq} Hz
              </span>
              <input
                type="range" min="20" max="200" step="5" value={hpfFreq}
                onChange={(e) => setHpfFreq(parseInt(e.target.value))}
                className="w-full accent-cyan-500"
              />
            </label>
          </div>
        </div>
      )}

      {/* ──── 본문 ──── */}
      <main className="flex-1 p-3 sm:p-6 max-w-4xl mx-auto w-full space-y-4 sm:space-y-6">

        {/* ─ 상태 바 ─ */}
        <div className="flex items-center gap-3 text-sm">
          <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${isActive ? "bg-green-900/50 text-green-400 border border-green-700/50" : "bg-gray-800 text-gray-500 border border-gray-700/50"}`}>
            <span className={`w-2 h-2 rounded-full ${isActive ? "bg-green-400 animate-pulse" : "bg-gray-600"}`} />
            {isActive ? "Live" : "Idle"}
          </div>
          {isActive && (
            <>
              <span className="text-gray-500 text-xs">
                {audioCtxRef.current?.sampleRate ? `${audioCtxRef.current.sampleRate / 1000}kHz` : ""}
              </span>
              <div className="flex items-center gap-1 text-xs text-gray-500">
                <Volume2 className="w-3 h-3" />
                <div className="w-16 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-75"
                    style={{
                      width: `${rmsLevel * 100}%`,
                      backgroundColor: rmsLevel > 0.8 ? "#ef4444" : rmsLevel > 0.5 ? "#eab308" : "#22c55e",
                    }}
                  />
                </div>
              </div>
            </>
          )}
        </div>

        {/* ─ Waveform ─ */}
        <section>
          <div className="flex items-center gap-2 mb-2">
            <Activity className="w-4 h-4 text-blue-400" />
            <h2 className="text-sm font-semibold text-gray-300">Waveform</h2>
          </div>
          {isActive ? (
            <WaveformCanvas analyser={analyserRef.current} isActive={isActive} />
          ) : (
            <div className="w-full h-32 sm:h-40 rounded-lg border border-gray-700/50 bg-gray-900 flex items-center justify-center text-gray-600 text-sm">
              <MicOff className="w-5 h-5 mr-2" /> Start Monitoring to see waveform
            </div>
          )}
        </section>

        {/* ─ 현재 노트 디스플레이 ─ */}
        <section className="text-center py-4 sm:py-8">
          {isActive && currentNote ? (
            <div className="space-y-2">
              <div className="flex items-center justify-center gap-1">
                <span
                  className="text-6xl sm:text-8xl font-black tracking-tight transition-colors duration-200"
                  style={{ color: noteColor }}
                >
                  {currentNote.name}
                </span>
                <span className="text-2xl sm:text-4xl font-bold text-gray-400 self-end pb-1 sm:pb-2">
                  {currentNote.octave}
                </span>
              </div>
              <p className="text-lg sm:text-xl text-gray-400 font-mono">
                {currentFreq.toFixed(1)} Hz
              </p>
              <CentsBar cents={currentNote.cents} />
              <p className="text-xs text-gray-600 mt-1">
                Clarity: {(currentClarity * 100).toFixed(0)}%
              </p>
            </div>
          ) : (
            <div className="space-y-3 py-4">
              <div className="text-5xl sm:text-7xl font-black text-gray-700">---</div>
              <p className="text-gray-600 text-sm">
                {isActive ? "Sing something..." : "Press Start Monitoring to begin"}
              </p>
            </div>
          )}
        </section>

        {/* ─ 피치 히스토리 그래프 ─ */}
        <section>
          <div className="flex items-center gap-2 mb-2">
            <BarChart3 className="w-4 h-4 text-purple-400" />
            <h2 className="text-sm font-semibold text-gray-300">Pitch History</h2>
            {pitchHistory.length > 0 && (
              <span className="text-xs text-gray-600 ml-auto">
                {pitchHistory.filter((d) => d.midi > 0).length} samples
              </span>
            )}
          </div>
          <PitchHistoryCanvas history={pitchHistory} />
        </section>

        {/* ─ 통계 카드 ─ */}
        {pitchHistory.length > 0 && (() => {
          const valid = pitchHistory.filter((d) => d.midi > 0);
          if (valid.length < 2) return null;
          const midis = valid.map((d) => d.midi);
          const avg = midis.reduce((a, b) => a + b, 0) / midis.length;
          const min = Math.min(...midis);
          const max = Math.max(...midis);
          const avgNote = frequencyToNote(A4_FREQ * Math.pow(2, (avg - A4_MIDI) / 12));
          const minNote = frequencyToNote(A4_FREQ * Math.pow(2, (min - A4_MIDI) / 12));
          const maxNote = frequencyToNote(A4_FREQ * Math.pow(2, (max - A4_MIDI) / 12));
          const variance = midis.reduce((s, m) => s + (m - avg) ** 2, 0) / midis.length;
          const std = Math.sqrt(variance);

          return (
            <section className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { label: "Average", value: avgNote?.fullName || "-", sub: `MIDI ${avg.toFixed(1)}` },
                { label: "Lowest", value: minNote?.fullName || "-", sub: `MIDI ${min.toFixed(1)}` },
                { label: "Highest", value: maxNote?.fullName || "-", sub: `MIDI ${max.toFixed(1)}` },
                { label: "Stability", value: std < 1 ? "Excellent" : std < 2 ? "Good" : std < 4 ? "Fair" : "Unstable", sub: `σ = ${std.toFixed(2)}` },
              ].map((card) => (
                <div key={card.label} className="bg-gray-900 border border-gray-800 rounded-lg p-3 text-center">
                  <p className="text-xs text-gray-500 mb-1">{card.label}</p>
                  <p className="text-lg font-bold text-gray-200">{card.value}</p>
                  <p className="text-xs text-gray-600">{card.sub}</p>
                </div>
              ))}
            </section>
          );
        })()}
      </main>

      {/* ──── 푸터 ──── */}
      <footer className="text-center text-xs text-gray-700 py-3 border-t border-gray-800/50">
        Web Audio API · Autocorrelation Pitch Detection · Zero External Dependencies
      </footer>
    </div>
  );
}
