/**
 * LoginRepositoryAdapter — hand-extended for me endpoints.
 */

import type { LoginRepository } from '@denselink/services/identity';
import type { AdapterDynamoDBClient } from '../_shared/dynamodb-client-types.js';
import { LoginRepositoryDdb } from './login-repository.ddb.js';

export class LoginRepositoryAdapter implements LoginRepository {
  private readonly ddb: LoginRepositoryDdb;

  constructor(private readonly dynamoClient: AdapterDynamoDBClient) {
    this.ddb = new LoginRepositoryDdb(this.dynamoClient);
  }

  async operatorLogin(
    input: Parameters<LoginRepository['operatorLogin']>[0]
  ): Promise<Awaited<ReturnType<LoginRepository['operatorLogin']>>> {
    return await this.ddb.operatorLogin(input);
  }

  async getOperatorMe(
    input: Parameters<LoginRepository['getOperatorMe']>[0]
  ): Promise<Awaited<ReturnType<LoginRepository['getOperatorMe']>>> {
    return await this.ddb.getOperatorMe(input);
  }

  async updateOperatorMe(
    input: Parameters<LoginRepository['updateOperatorMe']>[0]
  ): Promise<Awaited<ReturnType<LoginRepository['updateOperatorMe']>>> {
    return await this.ddb.updateOperatorMe(input);
  }
}
