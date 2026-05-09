/**
 * SSE proxy for requirement analysis.
 * Proxies the browser's SSE request to the internal FastAPI analyzer,
 * keeping the internal URL off the client.
 */

const API_BASE = process.env.API_URL ?? "http://localhost:8001";

export async function POST(request: Request) {
  const body = await request.json();

  const upstream = await fetch(`${API_BASE}/api/analyze/requirement`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!upstream.ok) {
    const text = await upstream.text();
    return new Response(JSON.stringify({ error: text }), {
      status: upstream.status,
      headers: { "Content-Type": "application/json" },
    });
  }

  // Pipe the SSE stream through
  return new Response(upstream.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
