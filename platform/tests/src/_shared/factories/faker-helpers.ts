/**
 * Faker Helpers for Deterministic Test Data
 *
 * Shared test utility for all domains.
 * Provides deterministic faker instance with seeding support.
 */

/**
 * Faker Helpers
 *
 * Provides deterministic faker instance with seeding support.
 */

import { faker } from "@faker-js/faker";

let fakerInstance: typeof faker | null = null;

/**
 * Seeds the faker instance for deterministic test data.
 *
 * @param seed - Seed value (default: 99999)
 */
export function seedFaker(seed: number = 99999): void {
  faker.seed(seed);
  fakerInstance = faker;
}

/**
 * Gets the seeded faker instance.
 * If not seeded, seeds with default value.
 *
 * @returns Faker instance
 */
export function getFaker(): typeof faker {
  if (!fakerInstance) {
    seedFaker();
  }
  return fakerInstance!;
}
