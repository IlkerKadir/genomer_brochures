import { describe, it, expect, vi, beforeEach } from "vitest";
import * as api from "./client.js";

beforeEach(() => { global.fetch = vi.fn(); });

function mockJson(obj) {
  global.fetch.mockResolvedValue({ ok: true, json: () => Promise.resolve(obj) });
}

describe("api client", () => {
  it("uploads files via FormData", async () => {
    mockJson({ session_id: "s1", files: [] });
    const res = await api.upload([new File(["x"], "a.pdf")]);
    expect(res.session_id).toBe("s1");
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toBe("/api/upload");
    expect(opts.method).toBe("POST");
    expect(opts.body instanceof FormData).toBe(true);
  });

  it("edits a segment with scope and force", async () => {
    mockJson({ ok: true });
    await api.editSegment("s1", "f1", "0:5", "Çeviri", "dict", true);
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toBe("/api/s1/f1/segment/0:5");
    expect(JSON.parse(opts.body)).toEqual({ tr: "Çeviri", scope: "dict", force: true });
  });

  it("builds page url with cache-bust", () => {
    const u = api.pageUrl("s1", "f1", 2);
    expect(u).toMatch(/^\/api\/s1\/f1\/page\/2\.png\?t=\d+/);
  });
});
