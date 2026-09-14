/**
 * HttpClient - HTTP client interface for adapters
 * 
 * This is a placeholder type definition for HTTP client implementations.
 * Actual implementations should be provided via dependency injection.
 */

export interface HttpClient {
  get<T = any>(url: string, config?: any): Promise<{ data: T }>;
  post<T = any>(url: string, data?: any, config?: any): Promise<{ data: T }>;
  put<T = any>(url: string, data?: any, config?: any): Promise<{ data: T }>;
  patch<T = any>(url: string, data?: any, config?: any): Promise<{ data: T }>;
  delete<T = any>(url: string, config?: any): Promise<{ data: T }>;
}
