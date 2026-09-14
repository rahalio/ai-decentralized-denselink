/**
 * Error handler — RFC7807 Problem Details.
 */

import type { FastifyError, FastifyRequest, FastifyReply } from 'fastify';

const ERROR_CODE_TO_STATUS: Record<string, number> = {
  NOT_FOUND: 404,
  BAD_REQUEST: 400,
  VALIDATION_ERROR: 422,
  PERMISSION_DENIED: 403,
  UNAUTHORIZED: 401,
  CONFLICT: 409,
  PACK_EMPTY: 422,
};

export function createErrorHandler() {
  return (
    error: FastifyError,
    request: FastifyRequest,
    reply: FastifyReply
  ): void => {
    try {
      request.log.error(error);

      const errorCode = (error as { code?: string }).code ?? error.code;
      const rawStatus =
        error.statusCode ??
        (typeof errorCode === 'string' && ERROR_CODE_TO_STATUS[errorCode]) ??
        500;
      const statusCode = typeof rawStatus === 'number' ? rawStatus : 500;
      const code =
        typeof errorCode === 'string' ? errorCode : 'INTERNAL_SERVER_ERROR';

      reply.status(statusCode).type('application/problem+json').send({
        type: `https://ddd-codegen-starter.local/problems/${code}`,
        title: error.name || 'Error',
        status: statusCode,
        detail: error.message,
        code,
        instance: request.url,
      });
    } catch (handlerError) {
      request.log.error(handlerError, 'Error handler failed');
      if (!reply.sent) {
        reply.status(500).type('application/problem+json').send({
          type: 'https://ddd-codegen-starter.local/problems/INTERNAL_SERVER_ERROR',
          title: 'Internal Server Error',
          status: 500,
          detail: 'Error handler failed',
          code: 'INTERNAL_SERVER_ERROR',
        });
      }
    }
  };
}
