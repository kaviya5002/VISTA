interface CacheEntry<T> { data: T; at: number; }
const _cache: Record<string, CacheEntry<unknown>> = {};

export const CACHE_TTL = {
  fleet:   30 * 1000,   // 30s  — matches backend TTL
  alerts:  30 * 1000,
  vehicle: 60 * 1000,   // 60s  — single vehicle is stable
  heavy:   60 * 1000,   // calendar, replay, technicians
};

export function getCached<T>(key: string, ttl = CACHE_TTL.fleet): T | null {
  const e = _cache[key];
  if (!e) return null;
  if (Date.now() - e.at > ttl) return null;
  return e.data as T;
}

export function setCached<T>(key: string, data: T): void {
  _cache[key] = { data, at: Date.now() };
}

export function invalidateCache(key: string): void {
  delete _cache[key];
}

export function invalidateVehicle(id: number): void {
  delete _cache[`vehicle_${id}`];
}
