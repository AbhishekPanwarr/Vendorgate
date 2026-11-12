import type { AuditEvent } from '../types';

/**
 * Deterministic string hash function for audit verification in browser and node.
 * Uses SHA-256 when SubtleCrypto or node crypto is available, with stable fallback.
 */
export async function computeEventHash(
  sequence: number,
  prevHash: string,
  timestamp: string,
  actor: string,
  eventType: string,
  payload: Record<string, unknown>
): Promise<string> {
  const content = JSON.stringify({
    seq: sequence,
    prev: prevHash,
    ts: timestamp,
    actor,
    type: eventType,
    data: payload
  });

  if (typeof crypto !== 'undefined' && crypto.subtle) {
    const encoder = new TextEncoder();
    const data = encoder.encode(content);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('').slice(0, 32);
  }

  // FNV-1a / Murmur deterministic fallback for offline/test environments
  let hash = 0x811c9dc5;
  for (let i = 0; i < content.length; i++) {
    hash ^= content.charCodeAt(i);
    hash += (hash << 1) + (hash << 4) + (hash << 7) + (hash << 8) + (hash << 24);
  }
  return ('00000000' + (hash >>> 0).toString(16)).slice(-8) + '000000000000000000000000';
}

/**
 * Verify complete cryptographic chain of audit events.
 * Returns { valid: true, count } or { valid: false, brokenAtSequence: N, reason }
 */
export async function verifyAuditChain(events: AuditEvent[]): Promise<{
  valid: boolean;
  count: number;
  brokenAtSequence?: number;
  reason?: string;
}> {
  if (!events || events.length === 0) {
    return { valid: true, count: 0 };
  }

  for (let i = 0; i < events.length; i++) {
    const event = events[i];
    const expectedPrev = i === 0 ? '00000000000000000000000000000000' : events[i - 1].hash;

    if (event.prevHash !== expectedPrev) {
      return {
        valid: false,
        count: events.length,
        brokenAtSequence: event.sequence,
        reason: `Previous hash mismatch at sequence ${event.sequence}: expected ${expectedPrev.slice(0, 8)}..., got ${event.prevHash.slice(0, 8)}...`
      };
    }

    const calculatedHash = await computeEventHash(
      event.sequence,
      event.prevHash,
      event.timestamp,
      event.actor,
      event.eventType,
      event.payload
    );

    if (calculatedHash !== event.hash) {
      return {
        valid: false,
        count: events.length,
        brokenAtSequence: event.sequence,
        reason: `Hash signature check failed at sequence ${event.sequence}`
      };
    }
  }

  return { valid: true, count: events.length };
}
