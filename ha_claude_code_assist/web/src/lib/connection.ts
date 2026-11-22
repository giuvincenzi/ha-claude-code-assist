import type { CoreEvent } from "./types";

type Pending = { resolve: (value: unknown) => void; reject: (error: Error) => void };

/**
 * WebSocket to the core: request/response commands plus pushed events.
 * Reconnects on its own; listeners are told when the state changes.
 */
export class Connection {
  state: "connecting" | "open" | "closed" = "connecting";
  private ws?: WebSocket;
  private nextId = 1;
  private pending = new Map<number, Pending>();
  private eventListeners = new Set<(event: CoreEvent) => void>();
  private stateListeners = new Set<() => void>();

  private readonly url: URL;

  constructor(url: URL) {
    this.url = url;
    this.connect();
  }

  request<T>(type: string, payload: Record<string, unknown> = {}): Promise<T> {
    if (this.state !== "open" || !this.ws) {
      return Promise.reject(new Error("not connected to the app"));
    }
    const id = this.nextId++;
    this.ws.send(JSON.stringify({ id, type, ...payload }));
    return new Promise<T>((resolve, reject) =>
      this.pending.set(id, { resolve: resolve as (value: unknown) => void, reject }),
    );
  }

  onEvent(listener: (event: CoreEvent) => void): () => void {
    this.eventListeners.add(listener);
    return () => this.eventListeners.delete(listener);
  }

  onState(listener: () => void): () => void {
    this.stateListeners.add(listener);
    return () => this.stateListeners.delete(listener);
  }

  private connect(): void {
    this.setState("connecting");
    const ws = new WebSocket(this.url);
    this.ws = ws;
    ws.onopen = () => this.setState("open");
    ws.onmessage = (message) => {
      const data = JSON.parse(message.data);
      if (data.type === "event") {
        this.eventListeners.forEach((listener) => listener(data.event as CoreEvent));
      } else if (data.type === "result") {
        const pending = this.pending.get(data.id);
        this.pending.delete(data.id);
        if (data.success) pending?.resolve(data.result);
        else pending?.reject(new Error(data.error));
      }
    };
    ws.onclose = () => {
      this.pending.forEach((pending) => pending.reject(new Error("connection lost")));
      this.pending.clear();
      this.setState("closed");
      setTimeout(() => this.connect(), 3000);
    };
  }

  private setState(state: Connection["state"]): void {
    this.state = state;
    this.stateListeners.forEach((listener) => listener());
  }
}

export function coreConnection(): Connection {
  // Relative URL: the panel is served under the Ingress path.
  const url = new URL("ws", window.location.href);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return new Connection(url);
}
