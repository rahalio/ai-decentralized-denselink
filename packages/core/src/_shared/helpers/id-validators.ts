/**
 * Zod validators for ULID-based domain IDs (DDD starter).
 */

import { z } from 'zod';
import type { DomainPrefix } from './id-contracts.js';
import { isValidDomainId } from './id-contracts.js';

export const ZodULID = z
  .string()
  .length(26, 'ULID must be exactly 26 characters')
  .regex(/^[0-9a-hjkmnp-tv-z]{26}$/, 'Invalid ULID format (must be lowercase)')
  .transform((val) => val.toLowerCase());

export function createDomainIdValidator(
  domainPrefix: DomainPrefix | 'usr',
  description?: string
) {
  const pattern = new RegExp(`^${domainPrefix}_[0-9a-hjkmnp-tv-z]{26}$`);
  return z
    .string()
    .length(
      30,
      'Domain-scoped ID must be 30 characters (3 prefix + 1 underscore + 26 ULID)'
    )
    .refine(
      (val) => pattern.test(val.toLowerCase()),
      `Invalid ${domainPrefix} ID format (expected: ${domainPrefix}_ulid)`
    )
    .refine(
      (val) =>
        domainPrefix === 'usr'
          ? /^usr_[0-9a-hjkmnp-tv-z]{26}$/.test(val.toLowerCase())
          : isValidDomainId(val.toLowerCase()),
      'Invalid domain ID'
    )
    .transform((val) => val.toLowerCase())
    .describe(description ?? `${domainPrefix} domain ID`);
}

export const ZodTntId = createDomainIdValidator('tnt', 'Tenant ID');
export const ZodAutId = createDomainIdValidator('aut', 'Auth ID');
export const ZodKeyId = createDomainIdValidator('key', 'API key ID');
export const ZodIdnId = createDomainIdValidator('idn', 'Identity ID');
export const ZodUsrId = createDomainIdValidator('usr', 'User ID');
