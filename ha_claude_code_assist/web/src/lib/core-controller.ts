import type { ReactiveController, ReactiveControllerHost } from "lit";

import type { Connection } from "./connection";
import type { CoreEvent } from "./types";

interface CoreHost extends ReactiveControllerHost {
  connection: Connection;
}

/**
 * Connects a view to the core for as long as it is on the page: `onOpen` runs when the
 * connection is (or becomes) open, `onEvent` for every event the core pushes.
 */
export class CoreController implements ReactiveController {
  private stops: Array<() => void> = [];
  private readonly host: CoreHost;
  private readonly handlers: { onOpen?: () => void; onEvent?: (event: CoreEvent) => void };

  constructor(host: CoreHost, handlers: { onOpen?: () => void; onEvent?: (event: CoreEvent) => void }) {
    this.host = host;
    this.handlers = handlers;
    host.addController(this);
  }

  hostConnected(): void {
    const { connection } = this.host;
    this.stops = [
      connection.onState(() => {
        this.host.requestUpdate();
        if (connection.state === "open") this.handlers.onOpen?.();
      }),
    ];
    if (this.handlers.onEvent) this.stops.push(connection.onEvent(this.handlers.onEvent));
    if (connection.state === "open") this.handlers.onOpen?.();
  }

  hostDisconnected(): void {
    this.stops.forEach((stop) => stop());
    this.stops = [];
  }
}
