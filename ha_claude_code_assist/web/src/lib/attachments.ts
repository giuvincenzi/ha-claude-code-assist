/** Files attached to a message: sent over HTTP, one request each, before the message itself. */

/** The most Home Assistant's Ingress lets through in one request. */
export const MAX_ATTACHMENT_BYTES = 16 * 1024 * 1024;
export const TOO_LARGE = "{name} is larger than 16 MB, the most Home Assistant lets through.";

const base = (sessionId: string) => `api/sessions/${encodeURIComponent(sessionId)}/attachments`;

/** Uploads a file into the session's attachments; returns the name it was saved under. */
export async function uploadAttachment(sessionId: string, file: File): Promise<string> {
  let response: Response;
  try {
    response = await fetch(`${base(sessionId)}?name=${encodeURIComponent(file.name)}`, {
      method: "POST", body: file, headers: { "Content-Type": "application/octet-stream" },
    });
  } catch {
    throw new Error(`${file.name} could not be sent, because the connection to the app was lost. Try again.`);
  }
  if (response.status === 413) throw new Error(TOO_LARGE.replace("{name}", file.name));
  if (!response.ok) {
    const error = await response.json().then((body) => body.error as string | undefined, () => undefined);
    throw new Error(error ?? `${file.name} could not be sent. Try again.`);
  }
  return (await response.json()).name;
}

/** The address of an attached picture, as the core serves it. */
export function attachmentUrl(sessionId: string, name: string): string {
  return `${base(sessionId)}/${encodeURIComponent(name)}`;
}

/** The address that downloads any attached file. */
export function attachmentDownloadUrl(sessionId: string, name: string): string {
  return `${attachmentUrl(sessionId, name)}/download`;
}
