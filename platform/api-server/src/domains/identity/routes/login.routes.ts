/**
 * Routes for Login / auth me — hand-extended.
 */

import type { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { getDependencyContainer } from '../../../infrastructure/dependency-container.js';
import {
  getOperatorMe,
  operatorLogin,
  updateOperatorMe,
} from '../handlers/login.handlers.js';
import { wrapHandlerInExecutionContext } from '../../../lib/execution-context-wrapper.js';

export async function loginRoutes(fastify: FastifyInstance) {
  fastify.post(
    '/v0/auth/login',
    { config: { scope: 'public' } },
    async (
      request: FastifyRequest<{
        Params: Record<string, string>;
        Querystring: Record<string, string | string[] | undefined>;
        Body: unknown;
      }>,
      reply: FastifyReply
    ) => {
      await wrapHandlerInExecutionContext(request, async () => {
        const deps =
          getDependencyContainer().getIdentityDependenciesForRequest();
        await operatorLogin(request, reply, deps);
      });
    }
  );

  fastify.get(
    '/v0/auth/me',
    { config: { scope: 'tenant' } },
    async (request: FastifyRequest, reply: FastifyReply) => {
      await wrapHandlerInExecutionContext(request, async () => {
        const deps =
          getDependencyContainer().getIdentityDependenciesForRequest();
        await getOperatorMe(request, reply, deps);
      });
    }
  );

  fastify.patch(
    '/v0/auth/me',
    { config: { scope: 'tenant' } },
    async (request: FastifyRequest, reply: FastifyReply) => {
      await wrapHandlerInExecutionContext(request, async () => {
        const deps =
          getDependencyContainer().getIdentityDependenciesForRequest();
        await updateOperatorMe(request, reply, deps);
      });
    }
  );
}
