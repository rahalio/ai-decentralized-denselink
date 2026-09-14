/**
 * DDD Codegen Starter API server — boots shared middleware + identity routes.
 */

import Fastify from 'fastify';
import cors from '@fastify/cors';
import helmet from '@fastify/helmet';
import { registerSecurityMiddleware } from './lib/middleware/security-middleware.js';
import { registerResponseEnvelope } from './lib/middleware/response-envelope.middleware.js';
import { setupServerLifecycle, startServer } from './lib/server-startup.js';
import { bootstrapInfrastructure } from './infrastructure/bootstrap.js';
import { registerAllDomainRoutes } from './lib/routes/domain-routes.js';
import './lib/types/fastify-types.js';

async function createApp() {
  const fastify = Fastify({
    logger: true,
    requestIdHeader: 'x-request-id',
    genReqId: () => crypto.randomUUID(),
  });

  await fastify.register(cors, {
    origin: true,
    methods: ['GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
    allowedHeaders: [
      'Content-Type',
      'X-API-Key',
      'Authorization',
      'Idempotency-Key',
    ],
  });
  await fastify.register(helmet, {
    global: true,
    crossOriginResourcePolicy: { policy: 'cross-origin' },
  });

  await bootstrapInfrastructure();
  await registerSecurityMiddleware(fastify);
  registerResponseEnvelope(fastify);
  setupServerLifecycle(fastify);

  fastify.get('/health', async () => ({
    status: 'ok',
    service: 'denselink-api',
  }));

  await registerAllDomainRoutes(fastify);

  return fastify;
}

const app = await createApp();
await startServer(app);
