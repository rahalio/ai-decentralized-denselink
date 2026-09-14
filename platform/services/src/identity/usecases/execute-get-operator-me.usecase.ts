/** ExecuteGetOperatorMe — hand-maintained. */

import type {
  GetOperatorMeInput,
  GetOperatorMeOutput,
} from '../dto/login.dto';
import type {
  ExecutionContextService,
  IdGeneratorService,
} from '@denselink/services/_shared/index.js';
import type { LoginRepository } from '../ports';
import { NotFoundError } from '../errors';

export class ExecuteGetOperatorMe {
  constructor(
    private readonly context: ExecutionContextService,
    private readonly idGenerator: IdGeneratorService,
    private readonly login: LoginRepository,
  ) {}

  async execute(input: GetOperatorMeInput = {}): Promise<GetOperatorMeOutput> {
    const correlationId = this.idGenerator.idnId();
    const result = await this.login.getOperatorMe({
      ...input,
      orgId: this.context.getOrgId(),
      userId: this.context.getUserId(),
      correlationId,
    } as unknown as GetOperatorMeInput);
    if (!result) throw new NotFoundError('Session not found');
    return result as GetOperatorMeOutput;
  }
}
