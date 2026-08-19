const TRUSTED_CLIENT_TOKEN = "6A5AA1D4EAFF4E9FB37E23D68491D6F4";
const SEC_MS_GEC_VERSION = "1-143.0.3650.75";
const WIN_EPOCH = 11644473600n;
const S_TO_NS = 1000000000n;

async function generateSecMsGec() {
  const unixSec = BigInt(Math.floor(Date.now() / 1000));
  let ticks = unixSec + WIN_EPOCH;
  ticks -= ticks % 300n; // Round down to nearest 5 minutes
  ticks *= S_TO_NS / 100n;

  const strToHash = `${ticks.toString()}${TRUSTED_CLIENT_TOKEN}`;
  const msgBuffer = new TextEncoder().encode(strToHash);
  const hashBuffer = await crypto.subtle.digest("SHA-256", msgBuffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("").toUpperCase();
}

function generateMuid() {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("")
    .toUpperCase();
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // 1. Handle CORS Preflight
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
          "Access-Control-Allow-Headers": "*",
        },
      });
    }

    const secMsGec = await generateSecMsGec();

    // 2. Voice List Endpoint: /voices
    if (url.pathname === "/voices" || url.pathname === "/api/voices") {
      const voiceListUrl = `https://speech.platform.bing.com/consumer/speech/synthesize/readaloud/voices/list?trustedclienttoken=${TRUSTED_CLIENT_TOKEN}&Sec-MS-GEC=${secMsGec}&Sec-MS-GEC-Version=${SEC_MS_GEC_VERSION}`;
      const res = await fetch(voiceListUrl, {
        headers: {
          Authority: "speech.platform.bing.com",
          "Sec-CH-UA": '" Not;A Brand";v="99", "Microsoft Edge";v="143", "Chromium";v="143"',
          "Sec-CH-UA-Mobile": "?0",
          Accept: "*/*",
          "Sec-Fetch-Site": "none",
          "Sec-Fetch-Mode": "cors",
          "Sec-Fetch-Dest": "empty",
          "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0",
          "Accept-Encoding": "gzip, deflate, br, zstd",
          "Accept-Language": "en-US,en;q=0.9",
          Cookie: `muid=${generateMuid()};`,
        },
      });
      const data = await res.text();
      return new Response(data, {
        status: res.status,
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*",
        },
      });
    }

    // 3. WebSocket Proxy to Bing Edge TTS
    const targetUrl = new URL(
      `https://speech.platform.bing.com/consumer/speech/synthesize/readaloud/edge/v1?TrustedClientToken=${TRUSTED_CLIENT_TOKEN}&Sec-MS-GEC=${secMsGec}&Sec-MS-GEC-Version=${SEC_MS_GEC_VERSION}`
    );

    const upgradeHeader = request.headers.get("Upgrade");
    if (upgradeHeader === "websocket") {
      const webSocketPair = new WebSocketPair();
      const [client, server] = Object.values(webSocketPair);

      const upstreamResp = await fetch(targetUrl.toString().replace(/^http/, "ws"), {
        headers: {
          Upgrade: "websocket",
          Origin: "chrome-extension://jdiccldimpdaibmpdkjnbmckianbfold",
          Pragma: "no-cache",
          "Cache-Control": "no-cache",
          "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0",
          Cookie: `muid=${generateMuid()};`,
        },
      });

      const upstreamWs = upstreamResp.webSocket;
      if (!upstreamWs) {
        return new Response("Failed to connect to upstream Microsoft WebSocket", { status: 502 });
      }

      upstreamWs.accept();
      server.accept();

      server.addEventListener("message", (event) => {
        try {
          upstreamWs.send(event.data);
        } catch (e) {}
      });

      upstreamWs.addEventListener("message", (event) => {
        try {
          server.send(event.data);
        } catch (e) {}
      });

      server.addEventListener("close", () => {
        try {
          upstreamWs.close();
        } catch (e) {}
      });

      upstreamWs.addEventListener("close", () => {
        try {
          server.close();
        } catch (e) {}
      });

      return new Response(null, {
        status: 101,
        webSocket: client,
        headers: {
          "Access-Control-Allow-Origin": "*",
        },
      });
    }

    return new Response("Edge TTS Cloudflare Proxy Active", {
      headers: { "Content-Type": "text/plain", "Access-Control-Allow-Origin": "*" },
    });
  },
};
