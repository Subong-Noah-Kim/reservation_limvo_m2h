// ─── 음악 상수 ───────────────────────────────────────────
export const NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
export const A4_FREQ = 440;
export const A4_MIDI = 69;

// Hz → 음악 노트 변환
export function frequencyToNote(freq) {
  if (freq <= 0) return null;
  const midi = 12 * Math.log2(freq / A4_FREQ) + A4_MIDI;
  const rounded = Math.round(midi);
  const name = NOTE_NAMES[((rounded % 12) + 12) % 12];
  const octave = Math.floor(rounded / 12) - 1;
  const cents = Math.round((midi - rounded) * 100);
  return { name, octave, cents, midi: rounded, fullName: `${name}${octave}` };
}

// ─── Autocorrelation 피치 감지 ───────────────────────────
export function detectPitch(buffer, sampleRate) {
  const SIZE = buffer.length;

  // RMS 기반 무음 감지 — 에너지가 너무 낮으면 무시
  let rms = 0;
  for (let i = 0; i < SIZE; i++) rms += buffer[i] * buffer[i];
  rms = Math.sqrt(rms / SIZE);
  if (rms < 0.01) return { freq: -1, clarity: 0 };

  // 신호 양 끝의 무음 트리밍 (정확도 향상)
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

  // 첫 번째 딥(dip)을 찾고, 그 이후의 피크를 탐색
  let foundDip = false;
  let maxVal = -1;
  let maxIdx = -1;
  const minLag = Math.floor(sampleRate / 1100); // ~1100Hz 상한
  const maxLag = Math.floor(sampleRate / 60);    // ~60Hz 하한

  for (let i = Math.max(1, minLag); i < Math.min(len, maxLag); i++) {
    if (!foundDip && corr[i] < corr[i - 1]) foundDip = true;
    if (foundDip && corr[i] > maxVal) {
      maxVal = corr[i];
      maxIdx = i;
    }
  }

  if (maxIdx === -1 || corr[0] === 0) return { freq: -1, clarity: 0 };

  // 파라볼릭 보간 (Parabolic Interpolation) — 정수 샘플 사이 정밀도 개선
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

// ─── 피치 → 색상 매핑 (크로매틱 컬러 휠) ─────────────────
export function noteToColor(noteName) {
  const colors = {
    C: "#ef4444", "C#": "#f97316", D: "#eab308", "D#": "#84cc16",
    E: "#22c55e", F: "#14b8a6", "F#": "#06b6d4", G: "#3b82f6",
    "G#": "#6366f1", A: "#8b5cf6", "A#": "#a855f7", B: "#ec4899",
  };
  return colors[noteName] || "#6b7280";
}

// ─── 사인파 생성 유틸 (테스트용) ──────────────────────────
export function generateSineWave(frequency, sampleRate, duration, amplitude = 0.8) {
  const length = Math.floor(sampleRate * duration);
  const buffer = new Float32Array(length);
  for (let i = 0; i < length; i++) {
    buffer[i] = amplitude * Math.sin(2 * Math.PI * frequency * i / sampleRate);
  }
  return buffer;
}
