import { describe, it, expect } from "vitest";
import {
  NOTE_NAMES,
  A4_FREQ,
  A4_MIDI,
  frequencyToNote,
  detectPitch,
  noteToColor,
  generateSineWave,
} from "../vocal-pitch-utils.js";

// ═══════════════════════════════════════════════════════════
// 1. frequencyToNote — 단위 테스트
// ═══════════════════════════════════════════════════════════
describe("frequencyToNote", () => {
  it("A4 (440Hz) → A4, cents=0", () => {
    const note = frequencyToNote(440);
    expect(note.name).toBe("A");
    expect(note.octave).toBe(4);
    expect(note.cents).toBe(0);
    expect(note.fullName).toBe("A4");
    expect(note.midi).toBe(69);
  });

  it("C4 (≈261.63Hz) → C4", () => {
    const note = frequencyToNote(261.63);
    expect(note.name).toBe("C");
    expect(note.octave).toBe(4);
    expect(note.fullName).toBe("C4");
    expect(Math.abs(note.cents)).toBeLessThanOrEqual(1);
  });

  it("E4 (≈329.63Hz) → E4", () => {
    const note = frequencyToNote(329.63);
    expect(note.name).toBe("E");
    expect(note.octave).toBe(4);
  });

  it("G#3 (≈207.65Hz) → G#3", () => {
    const note = frequencyToNote(207.65);
    expect(note.name).toBe("G#");
    expect(note.octave).toBe(3);
  });

  it("C3 (≈130.81Hz) → C3", () => {
    const note = frequencyToNote(130.81);
    expect(note.name).toBe("C");
    expect(note.octave).toBe(3);
  });

  it("B5 (≈987.77Hz) → B5", () => {
    const note = frequencyToNote(987.77);
    expect(note.name).toBe("B");
    expect(note.octave).toBe(5);
  });

  it("정확한 주파수에서 cents는 0에 가까워야 한다", () => {
    // A4 = 440, A3 = 220, A5 = 880 등 정확한 A 음
    [220, 440, 880].forEach((freq) => {
      const note = frequencyToNote(freq);
      expect(note.name).toBe("A");
      expect(note.cents).toBe(0);
    });
  });

  it("주파수가 약간 높으면 cents > 0", () => {
    const note = frequencyToNote(445); // A4보다 약간 높음
    expect(note.name).toBe("A");
    expect(note.cents).toBeGreaterThan(0);
  });

  it("주파수가 약간 낮으면 cents < 0", () => {
    const note = frequencyToNote(435); // A4보다 약간 낮음
    expect(note.name).toBe("A");
    expect(note.cents).toBeLessThan(0);
  });

  it("freq <= 0 이면 null 반환", () => {
    expect(frequencyToNote(0)).toBeNull();
    expect(frequencyToNote(-100)).toBeNull();
  });

  it("매우 낮은 주파수도 처리 가능 (C1 ≈ 32.7Hz)", () => {
    const note = frequencyToNote(32.7);
    expect(note.name).toBe("C");
    expect(note.octave).toBe(1);
  });

  it("매우 높은 주파수도 처리 가능 (C8 ≈ 4186Hz)", () => {
    const note = frequencyToNote(4186);
    expect(note.name).toBe("C");
    expect(note.octave).toBe(8);
  });

  it("MIDI 번호가 올바르게 계산된다", () => {
    // C4 = MIDI 60, D4 = 62, E4 = 64
    expect(frequencyToNote(261.63).midi).toBe(60);
    expect(frequencyToNote(293.66).midi).toBe(62);
    expect(frequencyToNote(329.63).midi).toBe(64);
  });

  it("12개 반음이 모두 정확히 매핑된다", () => {
    // C4부터 B4까지 12개 정확한 주파수
    const expectedNotes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
    const freqs = expectedNotes.map((_, i) => A4_FREQ * Math.pow(2, (60 + i - A4_MIDI) / 12));
    freqs.forEach((freq, i) => {
      const note = frequencyToNote(freq);
      expect(note.name).toBe(expectedNotes[i]);
    });
  });
});

// ═══════════════════════════════════════════════════════════
// 2. noteToColor — 단위 테스트
// ═══════════════════════════════════════════════════════════
describe("noteToColor", () => {
  it("모든 12개 노트에 대해 유효한 hex 색상을 반환한다", () => {
    NOTE_NAMES.forEach((name) => {
      const color = noteToColor(name);
      expect(color).toMatch(/^#[0-9a-f]{6}$/i);
    });
  });

  it("각 노트마다 고유한 색상을 반환한다", () => {
    const colors = NOTE_NAMES.map(noteToColor);
    const unique = new Set(colors);
    expect(unique.size).toBe(12);
  });

  it("알 수 없는 노트에는 회색 폴백(#6b7280)을 반환한다", () => {
    expect(noteToColor("X")).toBe("#6b7280");
    expect(noteToColor("")).toBe("#6b7280");
    expect(noteToColor("H")).toBe("#6b7280");
  });

  it("C → 빨간 계열, G → 파란 계열", () => {
    expect(noteToColor("C")).toBe("#ef4444");
    expect(noteToColor("G")).toBe("#3b82f6");
  });
});

// ═══════════════════════════════════════════════════════════
// 3. generateSineWave — 단위 테스트
// ═══════════════════════════════════════════════════════════
describe("generateSineWave", () => {
  it("올바른 길이의 버퍼를 생성한다", () => {
    const buf = generateSineWave(440, 44100, 0.1);
    expect(buf.length).toBe(4410); // 44100 * 0.1
  });

  it("Float32Array를 반환한다", () => {
    const buf = generateSineWave(440, 44100, 0.05);
    expect(buf).toBeInstanceOf(Float32Array);
  });

  it("진폭이 amplitude 매개변수 이내이다", () => {
    const amp = 0.5;
    const buf = generateSineWave(440, 44100, 0.1, amp);
    const maxVal = Math.max(...buf);
    const minVal = Math.min(...buf);
    expect(maxVal).toBeLessThanOrEqual(amp + 0.01);
    expect(minVal).toBeGreaterThanOrEqual(-amp - 0.01);
  });

  it("무음이 아닌 신호를 생성한다", () => {
    const buf = generateSineWave(440, 44100, 0.1);
    let rms = 0;
    for (let i = 0; i < buf.length; i++) rms += buf[i] * buf[i];
    rms = Math.sqrt(rms / buf.length);
    expect(rms).toBeGreaterThan(0.1);
  });
});

// ═══════════════════════════════════════════════════════════
// 4. detectPitch — 단위 테스트
// ═══════════════════════════════════════════════════════════
describe("detectPitch", () => {
  const sampleRate = 44100;

  it("무음 버퍼에서 freq=-1을 반환한다", () => {
    const silence = new Float32Array(2048); // 모두 0
    const result = detectPitch(silence, sampleRate);
    expect(result.freq).toBe(-1);
    expect(result.clarity).toBe(0);
  });

  it("매우 작은 노이즈에서 freq=-1을 반환한다 (RMS 임계값 이하)", () => {
    const noise = new Float32Array(2048);
    for (let i = 0; i < noise.length; i++) noise[i] = (Math.random() - 0.5) * 0.005;
    const result = detectPitch(noise, sampleRate);
    expect(result.freq).toBe(-1);
  });

  it("440Hz 사인파를 정확히 감지한다", () => {
    const buf = generateSineWave(440, sampleRate, 0.1);
    const result = detectPitch(buf, sampleRate);
    expect(result.freq).toBeGreaterThan(430);
    expect(result.freq).toBeLessThan(450);
    expect(result.clarity).toBeGreaterThan(0.8);
  });

  it("220Hz (A3) 사인파를 정확히 감지한다", () => {
    const buf = generateSineWave(220, sampleRate, 0.1);
    const result = detectPitch(buf, sampleRate);
    expect(result.freq).toBeGreaterThan(215);
    expect(result.freq).toBeLessThan(225);
    expect(result.clarity).toBeGreaterThan(0.8);
  });

  it("330Hz (E4 근처) 사인파를 감지한다", () => {
    const buf = generateSineWave(330, sampleRate, 0.1);
    const result = detectPitch(buf, sampleRate);
    expect(result.freq).toBeGreaterThan(320);
    expect(result.freq).toBeLessThan(340);
  });

  it("낮은 음 (100Hz) 사인파를 감지한다", () => {
    const buf = generateSineWave(100, sampleRate, 0.15);
    const result = detectPitch(buf, sampleRate);
    expect(result.freq).toBeGreaterThan(95);
    expect(result.freq).toBeLessThan(105);
  });

  it("높은 음 (880Hz, A5) 사인파를 감지한다", () => {
    const buf = generateSineWave(880, sampleRate, 0.05);
    const result = detectPitch(buf, sampleRate);
    expect(result.freq).toBeGreaterThan(870);
    expect(result.freq).toBeLessThan(890);
  });

  it("clarity 값은 0~1 범위 내이다", () => {
    const buf = generateSineWave(440, sampleRate, 0.1);
    const result = detectPitch(buf, sampleRate);
    expect(result.clarity).toBeGreaterThanOrEqual(0);
    expect(result.clarity).toBeLessThanOrEqual(1);
  });

  it("다양한 주파수에서 감지된 노트가 올바르다", () => {
    const testCases = [
      { freq: 261.63, expectedNote: "C" },
      { freq: 293.66, expectedNote: "D" },
      { freq: 349.23, expectedNote: "F" },
      { freq: 392.00, expectedNote: "G" },
      { freq: 440.00, expectedNote: "A" },
    ];
    testCases.forEach(({ freq, expectedNote }) => {
      const buf = generateSineWave(freq, sampleRate, 0.1);
      const result = detectPitch(buf, sampleRate);
      if (result.freq > 0) {
        const note = frequencyToNote(result.freq);
        expect(note.name).toBe(expectedNote);
      }
    });
  });

  it("작은 진폭 (0.3) 에서도 감지 가능하다", () => {
    const buf = generateSineWave(440, sampleRate, 0.1, 0.3);
    const result = detectPitch(buf, sampleRate);
    expect(result.freq).toBeGreaterThan(430);
    expect(result.freq).toBeLessThan(450);
  });
});

// ═══════════════════════════════════════════════════════════
// 5. 상수 검증
// ═══════════════════════════════════════════════════════════
describe("상수 값 검증", () => {
  it("NOTE_NAMES에 12개의 노트가 있다", () => {
    expect(NOTE_NAMES).toHaveLength(12);
  });

  it("NOTE_NAMES가 C부터 시작한다", () => {
    expect(NOTE_NAMES[0]).toBe("C");
    expect(NOTE_NAMES[11]).toBe("B");
  });

  it("A4_FREQ = 440", () => {
    expect(A4_FREQ).toBe(440);
  });

  it("A4_MIDI = 69", () => {
    expect(A4_MIDI).toBe(69);
  });
});
