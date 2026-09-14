/**
 * AWS credential provider for DynamoDB Document client construction.
 */

import { fromEnv, fromIni } from '@aws-sdk/credential-providers';

export function getAwsCredentialProvider() {
  if (process.env.AWS_ACCESS_KEY_ID && process.env.AWS_SECRET_ACCESS_KEY) {
    return fromEnv();
  }
  if (process.env.AWS_PROFILE || process.env.AWS_SDK_LOAD_CONFIG) {
    return fromIni({ profile: process.env.AWS_PROFILE });
  }
  // Default chain (env, SSO, instance role, …)
  return undefined;
}
