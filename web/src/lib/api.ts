export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "";
export const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL?.replace(/\/$/, "") ||
  (typeof window !== "undefined" ? `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}` : "");

export function getMediaUrl(path: string): string {
  if (!path) return "";
  return `${API_BASE_URL}/api/generate/media?path=${encodeURIComponent(path)}`;
}

export async function apiFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const response = await fetch(input, { ...init, credentials: "include" });
  if (response.status === 401 && typeof window !== "undefined") {
    window.dispatchEvent(new Event("studio:unauthorized"));
    throw new Error("Authentication required");
  }
  return response;
}
