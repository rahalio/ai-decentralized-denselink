/**
 * Meshports DDD Dependencies - Composition root (hand-fitted after Mode A).
 */

import { MeshportRepositoryAdapter } from "@denselink/adapters/meshports";
import { getIdGeneratorService } from "@denselink/adapters";
import type { AdapterDynamoDBClient } from "@denselink/adapters";
import { executionContextService } from "../../../lib/execution-context.service.js";
import {
  ExecuteAllocateMeshPort,
  ExecuteGetMeshPort,
  ExecuteListMeshPorts,
  ExecuteRevokeMeshPort,
} from "@denselink/services/meshports/usecases";
import type { MeshportRepository } from "@denselink/services/meshports/ports";

export interface MeshportsDomainModule {
  repos: {
    meshports: MeshportRepository;
  };
  useCases: {
    meshports: {
      create: ExecuteAllocateMeshPort;
      get: ExecuteGetMeshPort;
      list: ExecuteListMeshPorts;
      revoke: ExecuteRevokeMeshPort;
    };
  };
}

export function buildMeshportsDomainModule(
  dynamoClient: AdapterDynamoDBClient,
): MeshportsDomainModule {
  const repos = {
    meshports: new MeshportRepositoryAdapter(dynamoClient) as MeshportRepository,
  };

  const executionContext = executionContextService;
  const idGenerator = getIdGeneratorService();

  const useCases = {
    meshports: {
      create: new ExecuteAllocateMeshPort(
        executionContext,
        idGenerator,
        repos.meshports,
      ),
      get: new ExecuteGetMeshPort(executionContext, idGenerator, repos.meshports),
      list: new ExecuteListMeshPorts(
        executionContext,
        idGenerator,
        repos.meshports,
      ),
      revoke: new ExecuteRevokeMeshPort(
        executionContext,
        idGenerator,
        repos.meshports,
      ),
    },
  };
  return { repos, useCases };
}
