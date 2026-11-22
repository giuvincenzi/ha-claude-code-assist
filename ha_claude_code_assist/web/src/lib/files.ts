/** Saves a file from an address (one of the app's, or a preview made in the browser) under its name. */
export function saveFile(url: string, name: string): void {
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.append(link);
  link.click();
  link.remove();
}
