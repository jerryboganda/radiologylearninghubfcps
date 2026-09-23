import assert from 'node:assert/strict';
import test from 'node:test';
import { createAuthorizationUrl, createPkcePair } from './oidc-url.ts';

test('createAuthorizationUrl includes secure OIDC and PKCE parameters', () => {
  const result = new URL(
    createAuthorizationUrl({
      authorizationEndpoint: 'https://id.example/authorize',
      clientId: 'radbrain-web',
      redirectUri: 'http://localhost:3000/auth/callback',
      state: 'state-value',
      nonce: 'nonce-value',
      codeChallenge: 'challenge-value'
    })
  );

  assert.equal(result.origin + result.pathname, 'https://id.example/authorize');
  assert.equal(result.searchParams.get('response_type'), 'code');
  assert.equal(result.searchParams.get('scope'), 'openid profile email');
  assert.equal(result.searchParams.get('code_challenge_method'), 'S256');
  assert.equal(result.searchParams.get('state'), 'state-value');
  assert.equal(result.searchParams.get('nonce'), 'nonce-value');
});

test('createPkcePair creates a verifier within the RFC 7636 limit', async () => {
  const pair = await createPkcePair();
  assert.match(pair.verifier, /^[A-Za-z0-9_-]{43,128}$/u);
  assert.match(pair.challenge, /^[A-Za-z0-9_-]{43}$/u);
  assert.notEqual(pair.verifier, pair.challenge);
});

test('createPkcePair rejects invalid entropy', async () => {
  await assert.rejects(() => createPkcePair(8), RangeError);
});
