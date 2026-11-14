/**
 * Validation utilities for VendorGate.
 * Pure logic decoupled from React components for fast-feedback unit testing.
 */

export interface TaxIdValidationResult {
  valid: boolean;
  error?: string;
  normalized?: string;
}

/**
 * Validates US Employer Identification Number (EIN: XX-XXXXXXX or 9 digits)
 */
export function validateUSEIN(val: string): TaxIdValidationResult {
  const clean = val.replace(/[^0-9]/g, '');
  if (clean.length !== 9) {
    return { valid: false, error: 'US EIN must contain 9 digits (format XX-XXXXXXX)' };
  }
  // Disallowed prefix prefixes 00, 07, 08, 09, 17, 18, 19, 28, 29, 49, 69, 70, 78, 79, 89
  const prefix = clean.substring(0, 2);
  const invalidPrefixes = ['00', '07', '08', '09', '17', '18', '19', '28', '29', '49', '69', '70', '78', '79', '89'];
  if (invalidPrefixes.includes(prefix)) {
    return { valid: false, error: `US EIN prefix '${prefix}' is not assigned by the IRS` };
  }
  return { valid: true, normalized: `${clean.slice(0, 2)}-${clean.slice(2)}` };
}

/**
 * Validates EU VAT format (2-letter country code + alphanumeric up to 12 chars)
 */
export function validateEUVAT(val: string): TaxIdValidationResult {
  const clean = val.trim().toUpperCase().replace(/[\s.-]/g, '');
  if (clean.length < 4 || clean.length > 14) {
    return { valid: false, error: 'VAT number length must be between 4 and 14 characters' };
  }
  const country = clean.substring(0, 2);
  const euCountries = ['AT','BE','BG','CY','CZ','DE','DK','EE','EL','ES','FI','FR','HR','HU','IE','IT','LT','LU','LV','MT','NL','PL','PT','RO','SE','SI','SK','GB'];
  if (!euCountries.includes(country)) {
    return { valid: false, error: `Invalid VAT country prefix '${country}'` };
  }
  return { valid: true, normalized: clean };
}

/**
 * Validates Indian GSTIN (15 characters: 2-digit state code + 10-char PAN + entity code + Z + checksum)
 */
export function validateIndiaGSTIN(val: string): TaxIdValidationResult {
  const clean = val.trim().toUpperCase();
  const gstinRegex = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;
  if (!gstinRegex.test(clean)) {
    return { valid: false, error: 'GSTIN must be 15 characters matching state code + PAN + entity + Z + check' };
  }
  return { valid: true, normalized: clean };
}

/**
 * Universal Tax ID validator by country
 */
export function validateTaxId(country: string, taxId: string): TaxIdValidationResult {
  if (!taxId || !taxId.trim()) {
    return { valid: false, error: 'Tax ID is required' };
  }
  if (country === 'US') {
    return validateUSEIN(taxId);
  } else if (country === 'IN') {
    return validateIndiaGSTIN(taxId);
  } else if (['DE', 'FR', 'NL', 'IE', 'ES', 'IT', 'GB'].includes(country)) {
    return validateEUVAT(taxId);
  }
  // Generic fallback
  if (taxId.trim().length < 5) {
    return { valid: false, error: 'Tax ID must be at least 5 alphanumeric characters' };
  }
  return { valid: true, normalized: taxId.trim() };
}

/**
 * Validates US ABA routing number (9 digits with weighted checksum)
 * Checksum: (3*(d1 + d4 + d7) + 7*(d2 + d5 + d8) + (d3 + d6 + d9)) % 10 === 0
 */
export function validateUSRoutingNumber(routing: string): boolean {
  const clean = routing.replace(/[^0-9]/g, '');
  if (clean.length !== 9) return false;
  const d = clean.split('').map(Number);
  const checksum = (
    3 * (d[0] + d[3] + d[6]) +
    7 * (d[1] + d[4] + d[7]) +
    1 * (d[2] + d[5] + d[8])
  ) % 10;
  return checksum === 0;
}

/**
 * Validates standard IBAN using MOD-97 algorithm (ISO 7064)
 */
export function validateIBAN(iban: string): boolean {
  const clean = iban.replace(/[\s-]/g, '').toUpperCase();
  if (clean.length < 15 || clean.length > 34) return false;
  // Move the first four characters to the end
  const rearranged = clean.slice(4) + clean.slice(0, 4);
  // Convert letters to numbers (A=10, B=11, ..., Z=35)
  let numeric = '';
  for (let i = 0; i < rearranged.length; i++) {
    const code = rearranged.charCodeAt(i);
    if (code >= 65 && code <= 90) {
      numeric += (code - 55).toString();
    } else if (code >= 48 && code <= 57) {
      numeric += rearranged[i];
    } else {
      return false;
    }
  }
  // Compute mod 97 in chunks of numbers
  let remainder = 0;
  for (let i = 0; i < numeric.length; i += 7) {
    const chunk = remainder.toString() + numeric.substring(i, i + 7);
    remainder = parseInt(chunk, 10) % 97;
  }
  return remainder === 1;
}

/**
 * Mask account number to show only last 4 digits
 */
export function maskAccountNumber(val: string): string {
  const clean = val.trim();
  if (clean.length <= 4) return clean;
  const last4 = clean.slice(-4);
  return '••••' + last4;
}
