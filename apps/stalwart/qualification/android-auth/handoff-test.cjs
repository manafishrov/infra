#!/usr/bin/env node
'use strict';

// Runs the real upstream call sites with synthetic callbacks and HTTP responses.
// No Expo runtime, Android device, credentials, or production requests are used.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { stripTypeScriptTypes } = require('node:module');

const UPSTREAM_COMMIT = '6c82130267263a43aac885a701b4ed4d144b6092';
const SOURCE_PATH = 'src/lib/oauth.ts';
const WEBMAIL = 'https://mail.manafishrov.com';
const CONFIG = {
  oauthEnabled: true,
  oauthClientId: 'stalwart',
  jmapServerUrl: 'https://mail-admin.manafishrov.com',
  oauthIssuerUrl: 'https://id.manafishrov.com',
};
const METADATA = {
  issuer: CONFIG.oauthIssuerUrl,
  token_endpoint: 'https://id.manafishrov.com/api/oidc/token',
};
const BUNDLE = {
  flow: 'oauth',
  server_url: CONFIG.jmapServerUrl,
  access_token: 'FIXTURE-NOT-AN-ACCESS-TOKEN',
  refresh_token: 'FIXTURE-NOT-A-REFRESH-TOKEN',
  token_endpoint: METADATA.token_endpoint,
  client_id: CONFIG.oauthClientId,
};

function parseArgs() {
  const args = process.argv.slice(2);
  let checkout = process.env.BULWARK_NATIVE_CHECKOUT;
  let baseline = false;
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--baseline') baseline = true;
    else if (args[i] === '--checkout' && args[i + 1]) checkout = args[++i];
    else throw new Error(`Unknown or incomplete argument: ${args[i]}`);
  }
  if (!checkout) {
    throw new Error('Usage: node handoff-test.cjs --checkout PATH [--baseline] (or set BULWARK_NATIVE_CHECKOUT)');
  }
  return { checkout: path.resolve(checkout), baseline };
}

function loadSource({ checkout, baseline }) {
  const git = (...args) => execFileSync('git', ['-C', checkout, ...args], { encoding: 'utf8' }).trim();
  assert.equal(git('rev-parse', 'HEAD'), UPSTREAM_COMMIT, 'Checkout must be pinned to native 0.1.62 commit');
  const source = baseline
    ? git('show', `${UPSTREAM_COMMIT}:${SOURCE_PATH}`)
    : fs.readFileSync(path.join(checkout, SOURCE_PATH), 'utf8');
  // Replace only the known platform dependencies; keep the entire actual module,
  // including both callers and their state/credential parsing, in the test.
  const imports = [
    "import * as WebBrowser from 'expo-web-browser';",
    "import { secureFetch } from './client-cert';",
    "import { randomHex } from './random';",
  ];
  let moduleSource = source;
  for (const statement of imports) {
    assert.ok(moduleSource.includes(statement), `Upstream import changed: ${statement}`);
    moduleSource = moduleSource.replace(statement, '');
  }
  const js = stripTypeScriptTypes(moduleSource.replace(/^export /gm, ''));
  return new Function('WebBrowser', 'secureFetch', 'randomHex', `${js}\nreturn { runWebmailHandoff, redeemPairingCode };`);
}

async function run(makeApi, options = {}) {
  const {
    pair = false, change = {}, configChange = {}, metadataChange = {},
    badState = false, failFetch = false, responseStatus = 200,
    responseUrl, responseRedirected = false, responsePath, malformedJson = false,
  } = options;
  const bundle = { ...BUNDLE, ...change };
  const browser = {
    maybeCompleteAuthSession() {},
    async openAuthSessionAsync(url, redirectUri) {
      assert.equal(redirectUri, 'bulwarkmobile://auth/callback');
      const login = new URL(url);
      assert.equal(login.origin, WEBMAIL);
      assert.equal(login.pathname, '/login');
      assert.equal(login.searchParams.get('mobile_redirect_uri'), redirectUri);
      return {
        type: 'success',
        url: `${redirectUri}#${new URLSearchParams({
          ...bundle,
          state: badState ? 'wrong' : login.searchParams.get('mobile_state'),
        })}`,
      };
    },
  };
  const secureFetch = async (url, init) => {
    if (url === `${WEBMAIL}/api/auth/pair/redeem`) {
      assert.equal(init.method, 'POST');
      assert.deepEqual(JSON.parse(init.body), { pairing_code: 'FIXTURE-CODE' });
      return new Response(JSON.stringify(bundle));
    }
    assert.ok([
      `${WEBMAIL}/api/config`, `${WEBMAIL}/api/auth/oauth/metadata`,
    ].includes(url), 'Metadata must come only from the chosen webmail');
    assert.deepEqual(init.headers, { Accept: 'application/json' });
    assert.equal(init.body, undefined, 'Never send tokens with discovery');
    assert.equal(init.redirect, 'error');
    if (failFetch) throw new TypeError('Fixture network failure');
    const data = url.endsWith('/api/config')
      ? { ...CONFIG, ...configChange }
      : { ...METADATA, ...metadataChange };
    const response = new Response(malformedJson ? 'not json' : JSON.stringify(data), { status: responseStatus });
    const injectResponse = !responsePath || url.endsWith(responsePath);
    // Normal fetch reports its final URL. The client-certificate bridge instead
    // creates a Response with an empty URL, reproduced by responseUrl: ''.
    Object.defineProperty(response, 'url', {
      value: injectResponse && responseUrl !== undefined ? responseUrl : url,
    });
    Object.defineProperty(response, 'redirected', {
      value: injectResponse && responseRedirected,
    });
    return response;
  };
  const api = makeApi(browser, secureFetch, (size) => {
    assert.equal(size, 16);
    return 'fixed-fixture-state';
  });
  return pair
    ? api.redeemPairingCode(WEBMAIL, 'FIXTURE-CODE')
    : api.runWebmailHandoff(WEBMAIL);
}

async function main() {
  const options = parseArgs();
  const makeApi = loadSource(options);
  let passed = 0;
  let failed = 0;
  const test = async (name, body) => {
    try {
      await body();
      passed++;
    } catch (error) {
      failed++;
      console.error(`FAIL ${name}: ${error.message}`);
    }
  };
  const negatives = [
    ['foreign endpoint', { change: { token_endpoint: 'https://evil.example/token' } }],
    ['HTTP endpoint', { change: { token_endpoint: 'http://id.manafishrov.com/api/oidc/token' } }],
    ['altered endpoint query', { change: { token_endpoint: `${METADATA.token_endpoint}?evil=1` } }],
    ['hostname suffix spoof', { change: { token_endpoint: 'https://id.manafishrov.com.evil.example/token' } }],
    ['wrong client ID', { change: { client_id: 'wrong-audience' } }],
    ['wrong JMAP server', { change: { server_url: 'https://evil.example/jmap' } }],
    ['issuer mismatch', { metadataChange: { issuer: 'https://evil.example' } }],
    ['missing metadata issuer', { metadataChange: { issuer: undefined } }],
    ['HTTP configured issuer', { configChange: { oauthIssuerUrl: 'http://id.manafishrov.com' } }],
    ['userinfo endpoint', { change: { token_endpoint: 'https://user@id.manafishrov.com/api/oidc/token' } }],
    ['OAuth disabled', { configChange: { oauthEnabled: false } }],
    ['missing configured JMAP', { configChange: { jmapServerUrl: undefined } }],
    ['discovery network failure', { failFetch: true }],
    ['discovery HTTP error', { responseStatus: 503 }],
    ['discovery redirect response', { responseStatus: 302 }],
    ['discovery foreign final URL', { responseUrl: 'https://evil.example/api/config' }],
    ['config unavailable final URL', { responseUrl: '', responsePath: '/api/config' }],
    ['metadata unavailable final URL', { responseUrl: '', responsePath: '/api/auth/oauth/metadata' }],
    ['config redirected with matching final URL', { responseRedirected: true, responsePath: '/api/config' }],
    ['metadata redirected with matching final URL', { responseRedirected: true, responsePath: '/api/auth/oauth/metadata' }],
    ['discovery malformed JSON', { malformedJson: true }],
  ];
  for (const pair of [false, true]) {
    const flow = pair ? 'pairing' : 'handoff';
    await test(`${flow}: genuine external IdP`, async () => {
      const result = await run(makeApi, { pair });
      assert.equal(result.flow, 'oauth');
      assert.equal(result.serverUrl, CONFIG.jmapServerUrl);
      assert.equal(result.tokens.tokenEndpoint, METADATA.token_endpoint);
      assert.equal(result.tokens.clientId, CONFIG.oauthClientId);
      assert.equal(result.tokens.accessToken, BUNDLE.access_token);
      assert.equal(result.tokens.refreshToken, BUNDLE.refresh_token);
      assert.equal(result.tokens.source, pair ? 'pairing' : 'handoff');
    });
    await test(`${flow}: existing same-host flow`, async () => {
      const endpoint = `${CONFIG.jmapServerUrl}/auth/token`;
      const result = await run(makeApi, { pair, change: { token_endpoint: endpoint }, failFetch: true });
      assert.equal(result.tokens.tokenEndpoint, endpoint);
    });
    for (const [name, negative] of negatives) {
      await test(`${flow}: ${name}`, () => assert.rejects(
        run(makeApi, { pair, ...negative }), /token endpoint is not trusted/,
      ));
    }
  }
  await test('handoff: wrong state', () => assert.rejects(run(makeApi, { badState: true }), /State mismatch/));
  console.log(`${options.baseline ? 'BASELINE' : 'WORKTREE'}: ${passed} passed, ${failed} failed`);
  process.exitCode = failed ? 1 : 0;
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 2;
});
