/**
 * Slim API client matching generated webapp service call style:
 *   apiClient.get/post(url, { body?, signal? }) → ApiResponse<T>
 *
 * Always sends X-API-Key (demo default: denselink_demo_local_dev_key).
 * Optional Bearer token from localStorage after operator login.
 */

import type { ApiError, ApiResponse, RequestOptions } from "./types";
import { getEffectiveOrgId, setAuthOrgId, setCurrentOrgId } from "./tenant-state";

const TOKEN_KEY = "auth_token";
/** Prefer same-origin (Vite proxy) in the browser; fall back to local API. */
const DEFAULT_API_BASE =
  typeof window !== "undefined" ? "" : "http://127.0.0.1:4000";
const DEFAULT_API_KEY = "denselink_demo_local_dev_key";

function getApiBase(): string {
  if (typeof window !== "undefined") {
    const runtime = (window as { env?: { API_BASE_URL?: string } }).env
      ?.API_BASE_URL;
    if (typeof runtime === "string" && runtime.startsWith("http")) {
      return runtime.replace(/\/$/, "");
    }
  }
  try {
    const vite = import.meta.env?.VITE_API_BASE;
    if (typeof vite === "string") {
      if (vite === "") return "";
      if (vite.startsWith("http")) return vite.replace(/\/$/, "");
    }
  } catch {
    /* ignore */
  }
  return DEFAULT_API_BASE;
}

function getApiKey(): string {
  try {
    const vite = import.meta.env?.VITE_API_KEY;
    if (typeof vite === "string" && vite.length > 0) return vite;
  } catch {
    /* ignore */
  }
  return DEFAULT_API_KEY;
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export class ApiClient {
  /** Own-property methods so Vite HMR cannot leave a stale prototype. */
  setToken = (token: string) => {
    if (typeof window === "undefined") return;
    localStorage.setItem(TOKEN_KEY, token);
  };

  getToken = (): string | null => {
    return getToken();
  };

  clearToken = () => {
    if (typeof window === "undefined") return;
    localStorage.removeItem(TOKEN_KEY);
  };

  setOrgId = (orgId: string | null) => {
    setCurrentOrgId(orgId);
    setAuthOrgId(orgId);
    if (typeof window !== "undefined") {
      if (orgId) localStorage.setItem("orgId", orgId);
      else localStorage.removeItem("orgId");
    }
  };

  getOrgId = (): string | null => {
    return getEffectiveOrgId();
  };

  private async request<T>(
    endpoint: string,
    options: RequestOptions = {},
  ): Promise<ApiResponse<T>> {
    const base = getApiBase();
    const path = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
    const url = `${base}${path}`;

    const method = (options.method || "GET").toUpperCase();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "X-API-Key": getApiKey(),
      ...((options.headers as Record<string, string>) || {}),
    };
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
    if (
      ["POST", "PUT", "PATCH"].includes(method) &&
      !headers["Idempotency-Key"] &&
      !headers["idempotency-key"]
    ) {
      headers["Idempotency-Key"] =
        typeof crypto !== "undefined" && "randomUUID" in crypto
          ? crypto.randomUUID()
          : `idem_${Date.now()}`;
    }

    let body = options.body;
    if (body !== undefined && body !== null && typeof body !== "string") {
      body = JSON.stringify(body);
    }

    const { timeout: _timeout, headers: _headers, ...rest } = options;
    void _timeout;
    void _headers;

    const response = await fetch(url, {
      ...rest,
      method,
      headers,
      body: body as BodyInit | null | undefined,
    });

    if (!response.ok) {
      const errJson = (await response.json().catch(() => ({}))) as {
        error?: string;
        message?: string;
        code?: string;
      };
      const err: ApiError = {
        error: errJson.error || "Error",
        message: errJson.message || `HTTP ${response.status}`,
        statusCode: response.status,
        code: errJson.code,
      };
      throw Object.assign(new Error(err.message), err);
    }

    if (response.status === 204) {
      return { data: undefined as T };
    }

    const json = await response.json();
    if (json && typeof json === "object" && "data" in json) {
      return json as ApiResponse<T>;
    }
    return { data: json as T };
  }

  get = async <T>(
    endpoint: string,
    options?: RequestOptions,
  ): Promise<ApiResponse<T>> => {
    return this.request<T>(endpoint, { ...options, method: "GET" });
  };

  post = async <T>(
    endpoint: string,
    options?: RequestOptions,
  ): Promise<ApiResponse<T>> => {
    return this.request<T>(endpoint, { ...options, method: "POST" });
  };

  put = async <T>(
    endpoint: string,
    options?: RequestOptions,
  ): Promise<ApiResponse<T>> => {
    return this.request<T>(endpoint, { ...options, method: "PUT" });
  };

  patch = async <T>(
    endpoint: string,
    options?: RequestOptions,
  ): Promise<ApiResponse<T>> => {
    return this.request<T>(endpoint, { ...options, method: "PATCH" });
  };

  delete = async <T>(
    endpoint: string,
    options?: RequestOptions,
  ): Promise<ApiResponse<T>> => {
    return this.request<T>(endpoint, { ...options, method: "DELETE" });
  };
}

const g = globalThis as typeof globalThis & {
  __denselinkApiClient?: ApiClient;
};

/** HMR-stable singleton — reuse the same instance across Vite hot updates. */
export const apiClient: ApiClient = g.__denselinkApiClient ?? new ApiClient();

g.__denselinkApiClient = apiClient;

{
  const fresh = new ApiClient();
  apiClient.setToken = fresh.setToken;
  apiClient.getToken = fresh.getToken;
  apiClient.clearToken = fresh.clearToken;
  apiClient.setOrgId = fresh.setOrgId;
  apiClient.getOrgId = fresh.getOrgId;
  apiClient.get = fresh.get;
  apiClient.post = fresh.post;
  apiClient.put = fresh.put;
  apiClient.patch = fresh.patch;
  apiClient.delete = fresh.delete;
}
