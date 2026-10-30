// Sec-MS-GEC v2 token generation, ported 1:1 from edge-tts 7.3.1 (src/edge_tts/drm.py).
// Microsoft rotated this algorithm in Oct 2026: v1 tokens are rejected with HTTP 403.
// Keep in sync with upstream when Microsoft changes it again.

const TRUSTED_CLIENT_TOKEN = "6A5AA1D4EAFF4E9FB37E23D68491D6F4";
const WIN_EPOCH = 11644473600;
const S_TO_NS = 1e9;

const SHA256_INITIAL = [
  0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A, 0x510E527F, 0x9B05688C,
  0x1F83D9AB, 0x5BE0CD19,
];
const SHA256_STATE = [
  0xFD9FBEA2, 0x91243CE7, 0xBE499094, 0xCD2E1E0A, 0x6C006F49, 0x04BD35AB,
  0xFEB0A7E4, 0x03EFFBD2,
];
const SHA256_SCHEDULE = [
  0xEB24BF9E, 0x1558691F, 0xA0C09EE2, 0x0CFA32BA, 0xA622EE8C, 0xD1DD9491,
  0xC0DD25A0, 0xF9E70AB6, 0xF0C31573, 0x7058CE4E, 0x7188E606, 0x00E5AB33,
  0xD258B060, 0x72766564,
];
const SHA256_ROUND_CONSTANTS = [
  0x428A2F98, 0x71374491, 0xB5C0FBCF, 0xE9B5DBA5, 0x3956C25B, 0x59F111F1,
  0x923F82A4, 0xAB1C5ED5, 0xD807AA98, 0x12835B01, 0x243185BE, 0x550C7DC3,
  0x72BE5D74, 0x80DEB1FE, 0x9BDC06A7, 0xC19BF174, 0xE49B69C1, 0xEFBE4786,
  0x0FC19DC6, 0x240CA1CC, 0x2DE92C6F, 0x4A7484AA, 0x5CB0A9DC, 0x76F988DA,
  0x983E5152, 0xA831C66D, 0xB00327C8, 0xBF597FC7, 0xC6E00BF3, 0xD5A79147,
  0x06CA6351, 0x14292967, 0x27B70A85, 0x2E1B2138, 0x4D2C6DFC, 0x53380D13,
  0x650A7354, 0x766A0ABB, 0x81C2C92E, 0x92722C85, 0xA2BFE8A1, 0xA81A664B,
  0xC24B8B70, 0xC76C51A3, 0xD192E819, 0xD6990624, 0xF40E3585, 0x106AA070,
  0x19A4C116, 0x1E376C08, 0x2748774C, 0x34B0BCB5, 0x391C0CB3, 0x4ED8AA4A,
  0x5B9CCA4F, 0x682E6FF3, 0x748F82EE, 0x78A5636F, 0x84C87814, 0x8CC70208,
  0x90BEFFFA, 0xA4506CEB, 0xBEF9A3F7, 0xC67178F2,
];
const SHA256_BLOCK_CONSTANTS = [
  0x428A2F98, 0x71374491, 0xB5C0FBCF, 0xE9B5DBA5, 0x3956C25B, 0x59F111F1,
  0x923F82A4, 0xAB1C5ED5, 0xD807AA98, 0x12835B01, 0x243185BE, 0x550C7DC3,
  0x72BE5D74, 0x80DEB1FE, 0xC9DC06A7, 0xC19BF174, 0xE49B69C1, 0xEFBE4786,
  0x0FC19DC6, 0x240CA1CC, 0x2DE92C6F, 0x4A7484AA, 0x5CB0A9DC, 0x76F988DA,
  0x983E5152, 0xA831C66D, 0xB00327C8, 0xBF597FC7, 0xC6E00BF3, 0xD5A79147,
  0x06CA6351, 0x14292967, 0x27B70A85, 0x2E1B2138, 0x4D2C6DFC, 0x53380D13,
  0x650A7354, 0x766A0ABB, 0x81C2C92E, 0x92722C85, 0xA2BFE8A1, 0xA81A664B,
  0xC24B8B70, 0xC76C51A3, 0xD192E819, 0xD6990624, 0xF40E3585, 0x106AA070,
  0x19A4C116, 0x1E376C08, 0x2748774C, 0x34B0BCB5, 0x391C0CB3, 0x4ED8AA4A,
  0x5B9CCA4F, 0x682E6FF3, 0x748F82EE, 0x78A5636F, 0x84C87814, 0x8CC70208,
  0x90BEFFFA, 0xA4506CEB, 0xBEF9A3F7, 0xC67178F2,
];
const SHA256_ADJUSTMENT = 0xC9DC06A7;
const SHA256_SIGMA0_ADJUSTMENT = 0x059C0B80;
const SHA256_SIGMA1_ADJUSTMENT = 0x000B92C0;
const CS64_COEFFICIENTS = [
  [0xE82E91B1, 0xB32700D0],
  [0x44DE24C6, 0x88DFF51D],
  [0x3BEB65BC, 0x29514038],
  [0xC89C5933, 0xB328CBDF],
  [0x8D1EC211, 0xD405B4D5],
  [0x314EF5D5, 0x26E55F3C],
  [0xE92491B1, 0x607801C6],
  [0xF0A5B9D5, 0x82B2C1FB],
  [0x06064CF3, 0xFA51A3DA],
  [0xDA79FA60, 0x207CC464],
  [0xBED20560, 0x3C3C74F3],
  [0x89F9C9F8, 0xD2D14B61],
  [0x35FA38C6, 0xBB04A2C1],
  [0xCB49E3C6, 0xC5626167],
];
const CS64_FACTOR = 0x82893933;
const CS64_ADJUSTMENT0 = 0xF2F90B1A;
const CS64_ADJUSTMENT1 = 0x0B1A0000;

const rotr = (x, n) => ((x >>> n) | (x << (32 - n))) >>> 0;
const rotl16 = (x) => ((x << 16) | (x >>> 16)) >>> 0;
const add = (...xs) => {
  let s = 0;
  for (const x of xs) s = (s + (x >>> 0)) >>> 0;
  return s;
};
const mul = (a, b) => Math.imul(a, b) >>> 0;
const sigma0 = (x) => (rotr(x, 7) ^ rotr(x, 18) ^ (x >>> 3)) >>> 0;
const sigma1 = (x) => (rotr(x, 17) ^ rotr(x, 19) ^ (x >>> 10)) >>> 0;

function sha256Rounds(state, words, firstRound, constants) {
  let [a, b, c, d, e, f, g, h] = state;
  for (let i = firstRound; i < 64; i++) {
    const t1 = add(h, rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25), g ^ (e & (f ^ g)), constants[i], words[i]);
    const t2 = add(rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22), (a & b) | (c & (a | b)));
    h = g; g = f; f = e; e = add(d, t1); d = c; c = b; b = a; a = add(t1, t2);
  }
  return [a, b, c, d, e, f, g, h];
}

function expandSchedule(words, firstWord) {
  for (let i = firstWord; i < 64; i++) {
    words.push(add(words[i - 16], sigma0(words[i - 15]), words[i - 7], sigma1(words[i - 2])));
  }
  return words;
}

function sha256Init(prefix) {
  const words = new Array(16).fill(0);
  words[14] = (prefix[0] << 16) | (prefix[1] << 8) | prefix[2];
  words[15] = (prefix[3] << 24) | (prefix[4] << 16) | (prefix[5] << 8) | prefix[6];
  for (let i = 16; i < 30; i++) {
    let value = SHA256_SCHEDULE[i - 16];
    if (i - 2 >= 14) value = add(value, sigma1(words[i - 2]) ^ (i === 16 ? SHA256_SIGMA1_ADJUSTMENT : 0));
    if (i - 7 >= 14) value = add(value, words[i - 7]);
    if (i - 15 >= 14) value = add(value, sigma0(words[i - 15]) ^ (i === 29 ? SHA256_SIGMA0_ADJUSTMENT : 0));
    words.push(value);
  }
  words.push(add(sigma1(words[28]), words[23], sigma0(words[15]), words[14], SHA256_ADJUSTMENT, -SHA256_ROUND_CONSTANTS[14]));
  expandSchedule(words, 31);
  const working = sha256Rounds(SHA256_STATE, words, 14, SHA256_BLOCK_CONSTANTS);
  return SHA256_INITIAL.map((x, i) => add(x, working[i]));
}

function sha256Digest(data) {
  if (data.length < 7) throw new Error("Token salt must contain at least seven bytes");
  const length = 57 + data.length;
  const padded = Array.from(data.slice(7));
  padded.push(0x80);
  for (let i = 0; i < (((55 - length) % 64) + 64) % 64; i++) padded.push(0);
  const bits = BigInt(length) * 8n;
  for (let shift = 56n; shift >= 0n; shift -= 8n) padded.push(Number((bits >> shift) & 0xFFn));

  let state = sha256Init(data.slice(0, 7));
  for (let offset = 0; offset < padded.length; offset += 64) {
    const words = [];
    for (let i = 0; i < 16; i++) {
      const o = offset + i * 4;
      words.push(((padded[o] << 24) | (padded[o + 1] << 16) | (padded[o + 2] << 8) | padded[o + 3]) >>> 0);
    }
    expandSchedule(words, 16);
    const working = sha256Rounds(state, words, 0, SHA256_ROUND_CONSTANTS);
    state = state.map((x, i) => add(x, working[i]));
  }

  const out = new Uint8Array(32);
  state.forEach((word, i) => {
    out[i * 4] = (word >>> 24) & 0xff;
    out[i * 4 + 1] = (word >>> 16) & 0xff;
    out[i * 4 + 2] = (word >>> 8) & 0xff;
    out[i * 4 + 3] = word & 0xff;
  });
  return out;
}

function wordsLe4Even(data) {
  const padded = Array.from(data);
  while (padded.length % 4) padded.push(0);
  const words = [];
  for (let i = 0; i < padded.length; i += 4) {
    words.push((padded[i] | (padded[i + 1] << 8) | (padded[i + 2] << 16) | (padded[i + 3] << 24)) >>> 0);
  }
  if (words.length % 2) words.push(0);
  return words;
}

function cs64Digest(data, digest) {
  let keyA = (digest[0] | (digest[1] << 8) | (digest[2] << 16) | (digest[3] << 24)) >>> 0;
  let keyB = (digest[4] | (digest[5] << 8) | (digest[6] << 16) | (digest[7] << 24)) >>> 0;
  keyA = (keyA | 1) >>> 0;
  keyB = (keyB | 1) >>> 0;

  const factors = [mul(keyA, CS64_FACTOR), mul(keyB, CS64_FACTOR)];
  const terms = CS64_COEFFICIENTS.map(([c], i) => mul(c, factors[i % 2]));
  const offsets = CS64_COEFFICIENTS.map(([, o]) => o);

  const salt = new Uint8Array(data.length + 1);
  salt.set(data, 1);
  wordsLe4Even(salt).forEach((word, i) => {
    let term = mul(word, i % 2 === 0 ? keyA : keyB);
    let offset = mul(rotl16(word), i % 2 === 0 ? 0xef0569fb : 0xc31713db);
    if (i === 0) {
      term = add(term, mul(CS64_ADJUSTMENT0, factors[0]));
      offset = add(offset, CS64_ADJUSTMENT1);
    }
    terms.push(term);
    offsets.push(offset);
  });

  let swapAcc = 0, swapLast = 0, state = 0, acc = 0;
  for (let i = 0; i < terms.length; i += 2) {
    const x = terms[i], y = terms[i + 1];

    let t = rotl16(add(offsets[i], x));
    let q = mul(t, 0x76f50f34);
    swapAcc = add(swapAcc, mul(rotl16(q), 0xc3efea97), q);

    t = rotl16(add(offsets[i + 1], y));
    q = mul(t, 0x1881ce3c);
    swapLast = add(mul(rotl16(q), 0x35bd1ec9), q);
    swapAcc = add(swapAcc, swapLast);

    state = add(mul(state, keyA), x);
    state = mul(rotl16(state), 0xcf98b111);
    state = mul(rotl16(state), 0x87085b9f);
    state = mul(rotl16(state), 0x12ceb96d);
    state = mul(rotl16(state), 0x257e1d83);
    acc = add(acc, state);

    t = add(mul(state, keyB), y);
    t = mul(rotl16(t), 0xa27416f5);
    t = mul(rotl16(t), 0xd38396ff);
    state = mul(rotl16(mul(rotl16(t), 0x7c932b89)), 0xbfa49f69);
    acc = add(acc, state);
  }

  return [(swapLast ^ state) >>> 0, (swapAcc ^ acc) >>> 0];
}

const hex = (bytes) => Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("").toUpperCase();

export function generateSecMsGecV2(unixTimestamp) {
  let ticks = unixTimestamp === undefined ? Date.now() / 1000 : unixTimestamp;
  ticks += WIN_EPOCH;
  ticks -= ticks % 300;
  ticks *= S_TO_NS / 100;

  const salt = new TextEncoder().encode(`${ticks.toFixed(0)}${TRUSTED_CLIENT_TOKEN}`);
  const digest = sha256Digest(salt);
  const [a, b] = cs64Digest(salt, digest);
  const cs64 = [a, b].flatMap((word) => {
    const bytes = new Uint8Array(4);
    new DataView(bytes.buffer).setUint32(0, word, true);
    return Array.from(bytes);
  });

  return `${hex(cs64)}-${hex(digest)}`;
}
