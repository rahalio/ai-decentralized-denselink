/**
 * LoginRepository Port — hand-extended for GET/PATCH /v0/auth/me.
 */

import type {
  GetOperatorMeInput,
  GetOperatorMeOutput,
  OperatorLoginInput,
  OperatorLoginOutput,
  UpdateOperatorMeInput,
  UpdateOperatorMeOutput,
} from '../dto/login.dto';

export interface LoginRepository {
  operatorLogin(input: OperatorLoginInput): Promise<OperatorLoginOutput>;
  getOperatorMe(input: GetOperatorMeInput): Promise<GetOperatorMeOutput>;
  updateOperatorMe(
    input: UpdateOperatorMeInput,
  ): Promise<UpdateOperatorMeOutput>;
}

export type {
  GetOperatorMeInput,
  GetOperatorMeOutput,
  OperatorLoginInput,
  OperatorLoginOutput,
  UpdateOperatorMeInput,
  UpdateOperatorMeOutput,
} from '../dto/login.dto';
