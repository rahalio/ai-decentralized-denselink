import { z } from "zod";

export type ValidationResult<T> =
  | { success: true; data: T }
  | { success: false; error: z.ZodError };

export function validateSchema<T>(
  schema: z.ZodSchema<T>,
  data: unknown,
): ValidationResult<T> {
  const result = schema.safeParse(data);
  if (result.success) return { success: true, data: result.data };
  return { success: false, error: result.error };
}

export function validateApiResponse<T>(
  schema: z.ZodSchema<T>,
  response: unknown,
): ValidationResult<{ data: T; meta?: unknown }> {
  if (!response || typeof response !== "object") {
    return {
      success: false,
      error: new z.ZodError([
        { code: "custom", path: [], message: "Response is not an object" },
      ]),
    };
  }
  const responseObj = response as Record<string, unknown>;
  if (!("data" in responseObj)) {
    return {
      success: false,
      error: new z.ZodError([
        {
          code: "custom",
          path: ["data"],
          message: "Response missing 'data' field",
        },
      ]),
    };
  }
  const dataResult = schema.safeParse(responseObj.data);
  if (!dataResult.success) return { success: false, error: dataResult.error };
  return {
    success: true,
    data: { data: dataResult.data, meta: responseObj.meta },
  };
}

export function formatValidationError(error: z.ZodError): string {
  const issues = error.issues.map((issue) => {
    const path = issue.path.join(".");
    return `${path ? `${path}: ` : ""}${issue.message}`;
  });
  return `Validation failed:\n${issues.join("\n")}`;
}
