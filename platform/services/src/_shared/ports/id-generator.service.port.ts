/**
 * IdGeneratorService Port — Denselink prefixes.
 */

import type { DomainCode } from '@denselink/core/_shared/helpers';

export interface IdGeneratorService {
  tntId(): string;
  keyId(): string;
  idnId(): string;
  autId(): string;
  mptId(): string;
  licId(): string;
  denId(): string;
  venId(): string;
  grtId(): string;
  tlaId(): string;
  rptId(): string;
  generateIdForDomain(domainCode: DomainCode): string;
}
