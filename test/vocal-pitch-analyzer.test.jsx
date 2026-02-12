import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup, act } from "@testing-library/react";

// ─── Web Audio API Mock ──────────────────────────────────
function createMockAudioContext() {
  const gainNode = {
    gain: { value: 1 },
    connect: vi.fn(),
    disconnect: vi.fn(),
  };
  const biquadFilter = {
    type: "",
    frequency: { value: 0 },
    Q: { value: 0 },
    connect: vi.fn(),
    disconnect: vi.fn(),
  };
  const analyserNode = {
    fftSize: 2048,
    smoothingTimeConstant: 0,
    getFloatTimeDomainData: vi.fn((arr) => {
      // 440Hz 사인파 시뮬레이션
      for (let i = 0; i < arr.length; i++) {
        arr[i] = 0.5 * Math.sin(2 * Math.PI * 440 * i / 44100);
      }
    }),
    connect: vi.fn(),
    disconnect: vi.fn(),
  };
  const sourceNode = {
    connect: vi.fn(),
    disconnect: vi.fn(),
  };

  return {
    sampleRate: 44100,
    createGain: vi.fn(() => gainNode),
    createBiquadFilter: vi.fn(() => biquadFilter),
    createAnalyser: vi.fn(() => analyserNode),
    createMediaStreamSource: vi.fn(() => sourceNode),
    close: vi.fn(),
    _nodes: { gainNode, biquadFilter, analyserNode, sourceNode },
  };
}

function setupGlobalMocks() {
  const mockAudioCtx = createMockAudioContext();
  const mockStream = {
    getTracks: vi.fn(() => [{ stop: vi.fn() }]),
  };

  // AudioContext
  globalThis.AudioContext = vi.fn(() => mockAudioCtx);
  globalThis.webkitAudioContext = vi.fn(() => mockAudioCtx);

  // getUserMedia
  globalThis.navigator.mediaDevices = {
    getUserMedia: vi.fn(() => Promise.resolve(mockStream)),
  };

  // Canvas 2D context mock
  globalThis.HTMLCanvasElement.prototype.getContext = vi.fn(() => ({
    fillRect: vi.fn(),
    clearRect: vi.fn(),
    beginPath: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn(),
    stroke: vi.fn(),
    fill: vi.fn(),
    arc: vi.fn(),
    fillText: vi.fn(),
    createLinearGradient: vi.fn(() => ({ addColorStop: vi.fn() })),
    fillStyle: "",
    strokeStyle: "",
    lineWidth: 1,
    lineJoin: "",
    globalAlpha: 1,
    font: "",
    textAlign: "",
  }));

  // requestAnimationFrame — 콜백을 호출하지 않고 ID만 반환 (재귀 루프 방지)
  let rafId = 0;
  globalThis.requestAnimationFrame = vi.fn(() => ++rafId);
  globalThis.cancelAnimationFrame = vi.fn();

  return { mockAudioCtx, mockStream };
}

// lucide-react는 vitest.config.js의 alias로 test/__mocks__/lucide-react.jsx를 사용

// ═══════════════════════════════════════════════════════════
// 통합 테스트 — 컴포넌트 렌더링 & 상호작용
// ═══════════════════════════════════════════════════════════
describe("VocalPitchAnalyzer 컴포넌트", () => {
  let mocks;

  beforeEach(() => {
    mocks = setupGlobalMocks();
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  // 동적 import (mock 설정 후에 로드되어야 함)
  async function importApp() {
    const mod = await import("../vocal-pitch-analyzer.jsx");
    return mod.default;
  }

  // ─── 초기 렌더링 ──────────────────────────────────────
  describe("초기 렌더링", () => {
    it("타이틀 'Vocal Pitch Analyzer'가 표시된다", async () => {
      const App = await importApp();
      render(<App />);
      expect(screen.getByText("Vocal Pitch Analyzer")).toBeInTheDocument();
    });

    it("'Start Monitoring' 버튼이 표시된다", async () => {
      const App = await importApp();
      render(<App />);
      expect(screen.getByText("Start Monitoring")).toBeInTheDocument();
    });

    it("초기 상태는 Idle이다", async () => {
      const App = await importApp();
      render(<App />);
      expect(screen.getByText("Idle")).toBeInTheDocument();
    });

    it("초기 음정 표시는 '---' 이다", async () => {
      const App = await importApp();
      render(<App />);
      expect(screen.getByText("---")).toBeInTheDocument();
    });

    it("안내 메시지가 표시된다", async () => {
      const App = await importApp();
      render(<App />);
      expect(screen.getByText("Start Monitoring을 눌러 시작하세요")).toBeInTheDocument();
    });

    it("Waveform 섹션이 표시된다", async () => {
      const App = await importApp();
      render(<App />);
      expect(screen.getByText("Waveform")).toBeInTheDocument();
    });

    it("Pitch History 섹션이 표시된다", async () => {
      const App = await importApp();
      render(<App />);
      expect(screen.getByText("Pitch History")).toBeInTheDocument();
    });

    it("마이크 비활성 안내가 표시된다", async () => {
      const App = await importApp();
      render(<App />);
      expect(screen.getByText("Start Monitoring to see waveform")).toBeInTheDocument();
    });

    it("푸터 텍스트가 표시된다", async () => {
      const App = await importApp();
      render(<App />);
      expect(screen.getByText(/Autocorrelation Pitch Detection/)).toBeInTheDocument();
    });
  });

  // ─── 설정 패널 ────────────────────────────────────────
  describe("설정 패널", () => {
    it("Settings 버튼 클릭 시 설정 패널이 토글된다", async () => {
      const App = await importApp();
      render(<App />);

      // 초기에는 Gain 슬라이더가 없어야 한다
      expect(screen.queryByText(/Input Gain/)).not.toBeInTheDocument();

      // Settings 아이콘 버튼 클릭
      const settingsBtn = screen.getByTestId("icon-Settings").closest("button");
      fireEvent.click(settingsBtn);

      // 설정 패널이 나타남
      expect(screen.getByText(/Input Gain/)).toBeInTheDocument();
      expect(screen.getByText(/High-pass Filter/)).toBeInTheDocument();

      // 다시 클릭하면 닫힘
      fireEvent.click(settingsBtn);
      expect(screen.queryByText(/Input Gain/)).not.toBeInTheDocument();
    });

    it("Gain 슬라이더 기본값은 1.0이다", async () => {
      const App = await importApp();
      render(<App />);

      const settingsBtn = screen.getByTestId("icon-Settings").closest("button");
      fireEvent.click(settingsBtn);

      expect(screen.getByText("Input Gain: 1.0x")).toBeInTheDocument();
    });

    it("HPF 슬라이더 기본값은 85Hz이다", async () => {
      const App = await importApp();
      render(<App />);

      const settingsBtn = screen.getByTestId("icon-Settings").closest("button");
      fireEvent.click(settingsBtn);

      expect(screen.getByText("High-pass Filter: 85 Hz")).toBeInTheDocument();
    });
  });

  // ─── 모니터링 시작/중지 ────────────────────────────────
  describe("모니터링 시작/중지", () => {
    it("Start 버튼 클릭 시 getUserMedia가 호출된다", async () => {
      const App = await importApp();
      render(<App />);

      const startBtn = screen.getByText("Start Monitoring").closest("button");
      await act(async () => {
        fireEvent.click(startBtn);
      });

      expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledWith({
        audio: {
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false,
        },
      });
    });

    it("Start 클릭 후 AudioContext가 생성된다", async () => {
      const App = await importApp();
      render(<App />);

      const startBtn = screen.getByText("Start Monitoring").closest("button");
      await act(async () => {
        fireEvent.click(startBtn);
      });

      expect(globalThis.AudioContext).toHaveBeenCalledWith({
        latencyHint: "interactive",
        sampleRate: 44100,
      });
    });

    it("Start 후 오디오 체인이 올바르게 연결된다 (source → HPF → Gain → Analyser)", async () => {
      const App = await importApp();
      render(<App />);

      const startBtn = screen.getByText("Start Monitoring").closest("button");
      await act(async () => {
        fireEvent.click(startBtn);
      });

      const { sourceNode, biquadFilter, gainNode, analyserNode } = mocks.mockAudioCtx._nodes;

      // source → HPF
      expect(sourceNode.connect).toHaveBeenCalledWith(biquadFilter);
      // HPF → Gain
      expect(biquadFilter.connect).toHaveBeenCalledWith(gainNode);
      // Gain → Analyser
      expect(gainNode.connect).toHaveBeenCalledWith(analyserNode);
    });

    it("Start 후 High-pass filter 설정이 올바르다", async () => {
      const App = await importApp();
      render(<App />);

      const startBtn = screen.getByText("Start Monitoring").closest("button");
      await act(async () => {
        fireEvent.click(startBtn);
      });

      const { biquadFilter } = mocks.mockAudioCtx._nodes;
      expect(biquadFilter.type).toBe("highpass");
      expect(biquadFilter.frequency.value).toBe(85);
      expect(biquadFilter.Q.value).toBe(0.7);
    });

    it("Start 후 상태가 Live로 변경된다", async () => {
      const App = await importApp();
      render(<App />);

      const startBtn = screen.getByText("Start Monitoring").closest("button");
      await act(async () => {
        fireEvent.click(startBtn);
      });

      expect(screen.getByText("Live")).toBeInTheDocument();
    });

    it("Start 후 Stop 버튼이 표시된다", async () => {
      const App = await importApp();
      render(<App />);

      const startBtn = screen.getByText("Start Monitoring").closest("button");
      await act(async () => {
        fireEvent.click(startBtn);
      });

      expect(screen.getByText("Stop")).toBeInTheDocument();
      expect(screen.queryByText("Start Monitoring")).not.toBeInTheDocument();
    });

    it("Stop 클릭 시 AudioContext가 닫히고 Idle로 돌아간다", async () => {
      const App = await importApp();
      render(<App />);

      // Start
      const startBtn = screen.getByText("Start Monitoring").closest("button");
      await act(async () => {
        fireEvent.click(startBtn);
      });

      // Stop
      const stopBtn = screen.getByText("Stop").closest("button");
      await act(async () => {
        fireEvent.click(stopBtn);
      });

      expect(mocks.mockAudioCtx.close).toHaveBeenCalled();
      expect(screen.getByText("Idle")).toBeInTheDocument();
      expect(screen.getByText("Start Monitoring")).toBeInTheDocument();
    });

    it("Stop 시 미디어 스트림 트랙이 정지된다", async () => {
      const App = await importApp();
      render(<App />);

      const startBtn = screen.getByText("Start Monitoring").closest("button");
      await act(async () => {
        fireEvent.click(startBtn);
      });

      const stopBtn = screen.getByText("Stop").closest("button");
      await act(async () => {
        fireEvent.click(stopBtn);
      });

      expect(mocks.mockStream.getTracks).toHaveBeenCalled();
    });
  });

  // ─── getUserMedia 실패 처리 ────────────────────────────
  describe("에러 처리", () => {
    it("마이크 권한 거부 시 alert이 표시된다", async () => {
      navigator.mediaDevices.getUserMedia = vi.fn(() =>
        Promise.reject(new Error("Permission denied"))
      );
      globalThis.alert = vi.fn();

      const App = await importApp();
      render(<App />);

      const startBtn = screen.getByText("Start Monitoring").closest("button");
      await act(async () => {
        fireEvent.click(startBtn);
      });

      expect(globalThis.alert).toHaveBeenCalledWith(
        "마이크 접근에 실패했습니다. 브라우저 권한을 확인해 주세요."
      );
    });

    it("마이크 권한 거부 후에도 Idle 상태를 유지한다", async () => {
      navigator.mediaDevices.getUserMedia = vi.fn(() =>
        Promise.reject(new Error("Permission denied"))
      );
      globalThis.alert = vi.fn();

      const App = await importApp();
      render(<App />);

      const startBtn = screen.getByText("Start Monitoring").closest("button");
      await act(async () => {
        fireEvent.click(startBtn);
      });

      expect(screen.getByText("Idle")).toBeInTheDocument();
    });
  });

  // ─── 샘플레이트 표시 ──────────────────────────────────
  describe("실시간 표시", () => {
    it("모니터링 중 샘플레이트가 표시된다", async () => {
      const App = await importApp();
      render(<App />);

      const startBtn = screen.getByText("Start Monitoring").closest("button");
      await act(async () => {
        fireEvent.click(startBtn);
      });

      expect(screen.getByText("44.1kHz")).toBeInTheDocument();
    });

    it("모니터링 시작 시 requestAnimationFrame이 호출된다", async () => {
      const App = await importApp();
      render(<App />);

      const startBtn = screen.getByText("Start Monitoring").closest("button");
      await act(async () => {
        fireEvent.click(startBtn);
      });

      expect(globalThis.requestAnimationFrame).toHaveBeenCalled();
    });

    it("모니터링 중지 시 cancelAnimationFrame이 호출된다", async () => {
      const App = await importApp();
      render(<App />);

      const startBtn = screen.getByText("Start Monitoring").closest("button");
      await act(async () => {
        fireEvent.click(startBtn);
      });

      const stopBtn = screen.getByText("Stop").closest("button");
      await act(async () => {
        fireEvent.click(stopBtn);
      });

      expect(globalThis.cancelAnimationFrame).toHaveBeenCalled();
    });
  });
});
