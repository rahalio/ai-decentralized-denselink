/**
 * Shared API types used by generated domain services.
 */

export interface ApiError {
  error: string;
  message?: string;
  statusCode?: number;
  code?: string;
}

export interface ApiResponse<T> {
  data: T;
  meta?: {
    correlationId?: string;
    timestamp?: string;
    pagination?: {
      nextCursor?: string | null;
      prevCursor?: string | null;
      limit?: number;
      totalCount?: number;
    };
  };
}

export interface RequestOptions extends Omit<RequestInit, "body"> {
  timeout?: number;
  body?: BodyInit | null | unknown;
}
