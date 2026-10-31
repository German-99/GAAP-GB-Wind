// In development the Vite proxy forwards /api to the backend; in production set
// VITE_API_URL to the deployed backend URL.
const BASE = import.meta.env.VITE_API_URL ?? "";
 
export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}
 
export async function apiGet(path, params = {}, signal) {
  const url = new URL(`${BASE}${path}`, window.location.origin);
  for (const [key, value] of Object.entries(params)) {
    url.searchParams.set(key, value);
  }
  const res = await fetch(url, { signal });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      // the body was not JSON: keep the status text
    }
    throw new ApiError(res.status, typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.json();
}