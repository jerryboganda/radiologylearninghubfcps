export interface AuthorizationUrlOptions {
  authorizationEndpoint: string;
  clientId: string;
  redirectUri: string;
  state: string;
  nonce: string;
  codeChallenge: string;
}

/** Build a standards-compliant Keycloak authorization request. */
export function createAuthorizationUrl(options: AuthorizationUrlOptions): string {
  const url = new URL(options.authorizationEndpoint);
  url.search = new URLSearchParams({
    client_id: options.clientId,
    response_type: 'code',
    scope: 'openid profile email',
    redirect_uri: options.redirectUri,
    state: options.state,
    nonce: options.nonce,
    code_challenge: options.codeChallenge,
    code_challenge_method: 'S256'
  }).toString();
  return url.toString();
}

function toBase64Url(bytes: Uint8Array): string {
  return Buffer.from(bytes)
    .toString('base64')
    .replaceAll('+', '-')
    .replaceAll('/', '_')
    .replace(/=+$/u, '');
}

export interface PkcePair {
  verifier: string;
  challenge: string;
}

/** Generate a high-entropy PKCE verifier/challenge pair. */
export async function createPkcePair(randomBytes = 64): Promise<PkcePair> {
  if (randomBytes < 43 || randomBytes > 128) {
    throw new RangeError('PKCE entropy must produce a verifier between 43 and 128 characters');
  }

  const verifier = toBase64Url(crypto.getRandomValues(new Uint8Array(randomBytes)));
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier));
  return { verifier, challenge: toBase64Url(new Uint8Array(digest)) };
}
