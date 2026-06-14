export type HealthResponse = {
  status: string;
  service: string;
  database: string;
  redis: string;
};

export class ApiError extends Error {
  readonly status: number;
  readonly statusText: string;
  readonly body: unknown;

  constructor(status: number, statusText: string, body: unknown) {
    super(`API request failed: ${status} ${statusText}`);
    this.name = "ApiError";
    this.status = status;
    this.statusText = statusText;
    this.body = body;
  }
}

export function getApiBaseUrl(): string {
  const baseUrl =
    process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || "http://localhost:8000";
  return baseUrl.replace(/\/$/, "");
}

type ApiRequestOptions = RequestInit & {
  /** Next.js fetch cache hint for server components. */
  next?: { revalidate?: number | false; tags?: string[] };
};

export async function apiRequest<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const base = getApiBaseUrl();
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const url = `${base}${normalizedPath}`;

  const response = await fetch(url, options);

  if (!response.ok) {
    let body: unknown;
    const contentType = response.headers.get("content-type") ?? "";
    try {
      if (contentType.includes("application/json")) {
        body = await response.json();
      } else {
        body = await response.text();
      }
    } catch {
      body = null;
    }
    throw new ApiError(response.status, response.statusText, body);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return (await response.json()) as T;
  }

  return (await response.text()) as T;
}

export async function fetchHealth(): Promise<HealthResponse | null> {
  try {
    return await apiRequest<HealthResponse>("/health", {
      next: { revalidate: 30 },
    });
  } catch {
    return null;
  }
}
