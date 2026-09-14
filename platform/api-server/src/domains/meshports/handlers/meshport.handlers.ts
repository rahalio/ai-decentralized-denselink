/**
 * Handlers for Meshport (hand-fitted after Mode A).
 */

import type { FastifyRequest, FastifyReply } from "fastify";
import type { MeshportsDomainModule } from "../dependencies/meshports-ddd.dependencies.js";
import type {
  AllocateMeshPortInput,
  GetMeshPortInput,
  ListMeshPortsInput,
  RevokeMeshPortInput,
} from "@denselink/services/meshports";

export async function listMeshPorts(
  request: FastifyRequest<{
    Params: Record<string, string>;
    Querystring: {
      cursor?: string | string[];
      limit?: string | string[];
      appId?: string | string[];
    };
    Body: unknown;
  }>,
  reply: FastifyReply,
  deps: MeshportsDomainModule,
): Promise<void> {
  const input: ListMeshPortsInput = {
    ...(request.query ?? {}),
  };
  const result = await deps.useCases.meshports.list.execute(input);
  return reply.code(200).send(result);
}

export async function allocateMeshPort(
  request: FastifyRequest,
  reply: FastifyReply,
  deps: MeshportsDomainModule,
): Promise<void> {
  const input: AllocateMeshPortInput = {
    ...(request.body ?? {}),
  };
  const result = await deps.useCases.meshports.create.execute(input);
  return reply.code(201).send(result);
}

export async function getMeshPort(
  request: FastifyRequest<{
    Params: { meshPortId: string };
    Querystring: Record<string, string | string[] | undefined>;
    Body: unknown;
  }>,
  reply: FastifyReply,
  deps: MeshportsDomainModule,
): Promise<void> {
  const input: GetMeshPortInput = {
    meshPortId: request.params.meshPortId,
  };
  const result = await deps.useCases.meshports.get.execute(input);
  return reply.code(200).send(result);
}

export async function revokeMeshPort(
  request: FastifyRequest<{
    Params: { meshPortId: string };
    Querystring: Record<string, string | string[] | undefined>;
    Body: unknown;
  }>,
  reply: FastifyReply,
  deps: MeshportsDomainModule,
): Promise<void> {
  const input: RevokeMeshPortInput = {
    meshPortId: request.params.meshPortId,
  };
  const result = await deps.useCases.meshports.revoke.execute(input);
  return reply.code(200).send(result);
}
