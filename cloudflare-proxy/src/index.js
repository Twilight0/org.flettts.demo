export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // Handle CORS preflight
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

    // Target endpoint on Microsoft Bing TTS
    const targetUrl = new URL("https://speech.platform.bing.com/consumer/speech/synthesize/readaloud/edge/v1");
    targetUrl.search = url.search;

    const modifiedHeaders = new Headers(request.headers);
    modifiedHeaders.set("Origin", "chrome-extension://jdiccldimpdaibmpdkjnbmckianbfold");
    modifiedHeaders.set(
      "User-Agent",
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0"
    );

    const upgradeHeader = request.headers.get("Upgrade");
    if (upgradeHeader === "websocket") {
      // WebSocket proxying
      return fetch(targetUrl.toString().replace(/^http/, "ws"), {
        headers: modifiedHeaders,
      });
    }

    // Standard HTTP proxying
    try {
      const response = await fetch(targetUrl.toString(), {
        method: request.method,
        headers: modifiedHeaders,
        body: request.method !== "GET" && request.method !== "HEAD" ? request.body : undefined,
      });

      const responseHeaders = new Headers(response.headers);
      responseHeaders.set("Access-Control-Allow-Origin", "*");
      responseHeaders.set("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
      responseHeaders.set("Access-Control-Allow-Headers", "*");

      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: responseHeaders,
      });
    } catch (err) {
      return new Response(JSON.stringify({ error: err.message }), {
        status: 500,
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*",
        },
      });
    }
  },
};
