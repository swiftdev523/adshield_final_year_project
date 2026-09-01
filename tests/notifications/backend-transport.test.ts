import {
  createAnalyzeNotification,
} from "../../services/notifications/analyzeNotification";

function response(
  body: unknown,
  options: { ok?: boolean; status?: number; jsonRejects?: boolean } = {},
): Response {
  return {
    ok: options.ok ?? true,
    status: options.status ?? 200,
    json: options.jsonRejects
      ? jest.fn().mockRejectedValue(new Error("invalid json"))
      : jest.fn().mockResolvedValue(body),
  } as unknown as Response;
}

describe("notification backend transport", () => {
  it("posts only trimmed text to the exact endpoint and maps the raw model output name", async () => {
    const fetchMock = jest
      .fn()
      .mockResolvedValue(response({ prediction: "Spam", confidence: 87.5 }));
    const fetchImpl = fetchMock as unknown as typeof fetch;
    const analyze = createAnalyzeNotification({
      fetchImpl,
      apiBaseUrl: "http://backend.test///",
    });

    await expect(analyze("  claim your reward  ")).resolves.toEqual({
      prediction: "Spam",
      modelScorePercent: 87.5,
    });
    expect(fetchImpl).toHaveBeenCalledTimes(1);
    expect(fetchImpl).toHaveBeenCalledWith(
      "http://backend.test/analyze-notification",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: "claim your reward" }),
      },
    );

    const request = fetchMock.mock.calls[0][1] as RequestInit;
    expect(JSON.parse(request.body as string)).toEqual({
      text: "claim your reward",
    });
    expect(request.body).not.toContain("package");
    expect(request.body).not.toContain("confidence");
  });

  it("maps a backend network failure distinctly", async () => {
    const fetchImpl = jest
      .fn()
      .mockRejectedValue(new TypeError("Network request failed")) as unknown as typeof fetch;

    await expect(
      createAnalyzeNotification({ fetchImpl })("hello"),
    ).rejects.toMatchObject({
      name: "NotificationAnalysisError",
      kind: "network",
      status: null,
    });
  });

  it("preserves backend HTTP detail and status", async () => {
    const fetchImpl = jest.fn().mockResolvedValue(
      response(
        { detail: "Notification text was rejected." },
        { ok: false, status: 422 },
      ),
    ) as unknown as typeof fetch;

    await expect(
      createAnalyzeNotification({ fetchImpl })("hello"),
    ).rejects.toMatchObject({
      kind: "http",
      status: 422,
      message: "Notification text was rejected.",
    });
  });

  it.each([
    [{ prediction: "Suspicious", confidence: 70 }, "unsupported prediction"],
    [{ prediction: "Spam", confidence: -1 }, "negative score"],
    [{ prediction: "Ham", confidence: 101 }, "oversized score"],
    [{ prediction: "Spam", confidence: Number.NaN }, "non-finite score"],
    [{ prediction: "Ham", confidence: "90" }, "non-number score"],
    [{ prediction: "Ham" }, "missing score"],
    [null, "null response"],
  ])("rejects %s (%s)", async (body, _description) => {
    const fetchImpl = jest
      .fn()
      .mockResolvedValue(response(body)) as unknown as typeof fetch;
    await expect(
      createAnalyzeNotification({ fetchImpl })("hello"),
    ).rejects.toMatchObject({ kind: "invalid-response" });
  });

  it("rejects invalid JSON returned with a successful status", async () => {
    const fetchImpl = jest
      .fn()
      .mockResolvedValue(response(null, { jsonRejects: true })) as unknown as typeof fetch;
    await expect(
      createAnalyzeNotification({ fetchImpl })("hello"),
    ).rejects.toEqual(
      expect.objectContaining({
        name: "NotificationAnalysisError",
        kind: "invalid-response",
      }),
    );
  });

  it("rejects empty input without making a request", async () => {
    const fetchImpl = jest.fn() as unknown as typeof fetch;
    await expect(
      createAnalyzeNotification({ fetchImpl })("   "),
    ).rejects.toMatchObject({ kind: "invalid-request" });
    expect(fetchImpl).not.toHaveBeenCalled();
  });
});
