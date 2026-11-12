import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useWebSocket } from "@/lib/websocket";

// WebSocket falso: guarda as instâncias para o teste abrir, mandar mensagem e fechar à mão.
class FakeWebSocket {
  static instances: FakeWebSocket[] = [];
  static OPEN = 1;
  readyState = FakeWebSocket.OPEN;
  sent: string[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: ((e: { code: number }) => void) | null = null;
  onerror: (() => void) | null = null;

  constructor(public url: string) {
    FakeWebSocket.instances.push(this);
  }
  send(data: string) {
    this.sent.push(data);
  }
  close() {}

  serverSends(payload: object) {
    this.onmessage?.({ data: JSON.stringify(payload) });
  }
  serverCloses(code: number) {
    this.onclose?.({ code });
  }
  authToken() {
    return JSON.parse(this.sent[0]).token;
  }
}

const flush = () => act(async () => {});

function mount(props: {
  token: string;
  onTokenExpired: () => Promise<string | null>;
}) {
  return renderHook(
    (p: typeof props) =>
      useWebSocket({
        channels: ["billing:2026-09"],
        accessToken: p.token,
        onMessage: () => {},
        onTokenExpired: p.onTokenExpired,
      }),
    { initialProps: props },
  );
}

describe("useWebSocket", () => {
  beforeEach(() => {
    FakeWebSocket.instances = [];
    vi.stubGlobal("WebSocket", FakeWebSocket);
  });
  afterEach(() => vi.unstubAllGlobals());

  it("manda o token na primeira mensagem e não na URL", () => {
    mount({ token: "t1", onTokenExpired: async () => null });
    const ws = FakeWebSocket.instances[0];
    act(() => ws.onopen?.());

    expect(ws.url.endsWith("/ws")).toBe(true);
    expect(ws.url).not.toContain("t1");
    expect(ws.authToken()).toBe("t1");
  });

  it("reconecta com o token que a renovação devolveu quando o back fecha com 4003", async () => {
    const onTokenExpired = vi.fn(async () => "t2");
    mount({ token: "t1", onTokenExpired });
    act(() => FakeWebSocket.instances[0].onopen?.());
    act(() =>
      FakeWebSocket.instances[0].serverSends({ type: "auth_ok", sub: "x" }),
    );

    // O ref ainda tem t1 (o render com t2 não aconteceu): o fluxo não pode depender dele.
    act(() => FakeWebSocket.instances[0].serverCloses(4003));
    await flush();

    expect(onTokenExpired).toHaveBeenCalledTimes(1);
    expect(FakeWebSocket.instances).toHaveLength(2);
    act(() => FakeWebSocket.instances[1].onopen?.());
    expect(FakeWebSocket.instances[1].authToken()).toBe("t2");
  });

  it("reconecta sem renovar quando o token já foi trocado pelo auth-context", async () => {
    const onTokenExpired = vi.fn(async () => "outro");
    const { rerender } = mount({ token: "t1", onTokenExpired });
    act(() => FakeWebSocket.instances[0].onopen?.());

    rerender({ token: "t2", onTokenExpired });
    act(() => FakeWebSocket.instances[0].serverCloses(4003));
    await flush();

    expect(onTokenExpired).not.toHaveBeenCalled();
    act(() => FakeWebSocket.instances[1].onopen?.());
    expect(FakeWebSocket.instances[1].authToken()).toBe("t2");
  });

  it("não reconecta quando a renovação falha (sessão revogada)", async () => {
    mount({ token: "t1", onTokenExpired: async () => null });
    act(() => FakeWebSocket.instances[0].onopen?.());

    act(() => FakeWebSocket.instances[0].serverCloses(4003));
    await flush();

    expect(FakeWebSocket.instances).toHaveLength(1);
  });

  it("auth_error seguido de 4003 não renova nem reconecta (sem laço)", async () => {
    const onTokenExpired = vi.fn(async () => "t2");
    mount({ token: "t1", onTokenExpired });
    act(() => FakeWebSocket.instances[0].onopen?.());

    act(() =>
      FakeWebSocket.instances[0].serverSends({
        type: "auth_error",
        reason: "x",
      }),
    );
    act(() => FakeWebSocket.instances[0].serverCloses(4003));
    await flush();

    expect(onTokenExpired).not.toHaveBeenCalled();
    expect(FakeWebSocket.instances).toHaveLength(1);
  });
});
