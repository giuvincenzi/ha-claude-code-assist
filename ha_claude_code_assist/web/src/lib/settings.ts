import type { Connection } from "./connection";
import type { SettingsView } from "./types";

export function loadSettings(connection: Connection): Promise<SettingsView> {
  return connection.request<SettingsView>("settings/get");
}

/**
 * Saves some settings (the core merges them with the others and saves the complete options
 * through the Supervisor). Returns the settings as saved; every open panel then gets a
 * `settings_changed` event.
 */
export function saveSettings(connection: Connection, changes: Record<string, unknown>): Promise<SettingsView> {
  return connection.request<SettingsView>("settings/update", { changes });
}
