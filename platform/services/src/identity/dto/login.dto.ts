/**
 * Login DTOs — hand-extended for session me (core-only codegen policy).
 */

import type {
  OperatorLoginRequestInput,
  UpdateOperatorMeRequestInput,
} from '@denselink/core/identity/types';

export type OperatorLoginInput = OperatorLoginRequestInput;
export type OperatorLoginOutput = {};

export type GetOperatorMeInput = Record<string, never>;
export type GetOperatorMeOutput = {};

export type UpdateOperatorMeInput = UpdateOperatorMeRequestInput;
export type UpdateOperatorMeOutput = {};
