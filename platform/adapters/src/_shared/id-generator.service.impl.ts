/**
 * ID Generator Service Implementation — Denselink prefixes.
 */

import type { DomainCode } from '@denselink/core/_shared/helpers';
import { DOMAIN_PREFIX_MAP, isValidDomainId } from '@denselink/core';
import { ulid } from 'ulid';
import type { IdGeneratorService } from '@denselink/services/_shared';

export function generateIdWithPrefix(prefix: string): string {
  if (!prefix || prefix.length !== 3 || !/^[a-z]{3}$/.test(prefix)) {
    throw new Error(
      `Invalid domain prefix: "${prefix}". Must be exactly 3 lowercase letters.`
    );
  }
  const id = `${prefix}_${ulid().toLowerCase()}`;
  if (!isValidDomainId(id)) {
    throw new Error(`Generated ID "${id}" failed validation.`);
  }
  return id;
}

export class DefaultIdGeneratorService implements IdGeneratorService {
  tntId(): string {
    return generateIdWithPrefix(DOMAIN_PREFIX_MAP.tenant);
  }
  keyId(): string {
    return generateIdWithPrefix(DOMAIN_PREFIX_MAP.apiKey);
  }
  idnId(): string {
    return generateIdWithPrefix(DOMAIN_PREFIX_MAP.identity);
  }
  autId(): string {
    return generateIdWithPrefix(DOMAIN_PREFIX_MAP.auth);
  }
  mptId(): string {
    return generateIdWithPrefix(DOMAIN_PREFIX_MAP.meshport);
  }
  licId(): string {
    return generateIdWithPrefix(DOMAIN_PREFIX_MAP.license);
  }
  denId(): string {
    return generateIdWithPrefix(DOMAIN_PREFIX_MAP.density);
  }
  venId(): string {
    return generateIdWithPrefix(DOMAIN_PREFIX_MAP.venue);
  }
  grtId(): string {
    return generateIdWithPrefix(DOMAIN_PREFIX_MAP.grant);
  }
  tlaId(): string {
    return generateIdWithPrefix(DOMAIN_PREFIX_MAP.telemetry);
  }
  rptId(): string {
    return generateIdWithPrefix(DOMAIN_PREFIX_MAP.report);
  }
  generateIdForDomain(domainCode: DomainCode): string {
    return generateIdWithPrefix(DOMAIN_PREFIX_MAP[domainCode]);
  }
}

let idGeneratorService: DefaultIdGeneratorService | null = null;

export function getIdGeneratorService(): DefaultIdGeneratorService {
  if (!idGeneratorService) {
    idGeneratorService = new DefaultIdGeneratorService();
  }
  return idGeneratorService;
}
