/** ExecuteUpdateOperatorMe — hand-maintained. */

import type {
  UpdateOperatorMeInput,
  UpdateOperatorMeOutput,
} from '../dto/login.dto';
import type {
  ExecutionContextService,
  IdGeneratorService,
} from '@denselink/services/_shared/index.js';
import type { LoginRepository } from '../ports';
import { NotFoundError, ValidationError } from '../errors';

export class ExecuteUpdateOperatorMe {
  constructor(
    private readonly context: ExecutionContextService,
    private readonly idGenerator: IdGeneratorService,
    private readonly login: LoginRepository,
  ) {}

  async execute(
    input: UpdateOperatorMeInput,
  ): Promise<UpdateOperatorMeOutput> {
    const correlationId = this.idGenerator.idnId();
    if (!input?.displayName?.trim()) {
      throw new ValidationError('displayName is required');
    }
    const result = await this.login.updateOperatorMe({
      ...input,
      orgId: this.context.getOrgId(),
      userId: this.context.getUserId(),
      correlationId,
    } as unknown as UpdateOperatorMeInput);
    if (!result) throw new NotFoundError('Session not found');
    return result as UpdateOperatorMeOutput;
  }
}
