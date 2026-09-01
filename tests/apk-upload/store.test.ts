import { mapUploadApkResponse } from "../../lib/scan/mapUploadApkResponse";
import type {
  ApkUploadAsset,
  UploadApkCallbacks,
  UploadApkRequest,
  uploadApk,
} from "../../services/apk/uploadApk";
import { createScanStore } from "../../store/useScanStore";
import type { ScanAssessment } from "../../types/scan-assessment";
import { uploadResponse } from "./fixtures";

const asset: ApkUploadAsset = {
  uri: "file:///downloads/sample.apk",
  name: "sample.apk",
  mimeType: "application/vnd.android.package-archive",
};

const assessment = mapUploadApkResponse(uploadResponse());

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

function asUploader(
  implementation: (
    request: UploadApkRequest,
    callbacks?: UploadApkCallbacks,
  ) => Promise<ScanAssessment>,
) {
  return jest.fn(implementation) as unknown as typeof uploadApk;
}

describe("APK scan store", () => {
  it("transitions selected -> uploading -> analysing -> success", async () => {
    const pending = deferred<ScanAssessment>();
    let callbacks: UploadApkCallbacks | undefined;
    const uploader = asUploader((request, suppliedCallbacks) => {
      expect(request).toEqual({ asset, installSource: "apk_sideload" });
      callbacks = suppliedCallbacks;
      return pending.promise;
    });
    const recordSuccessfulScan = jest.fn().mockResolvedValue(true);
    const store = createScanStore({ uploadApk: uploader, recordSuccessfulScan });

    store.getState().selectApk(asset);
    expect(store.getState().process).toEqual({ status: "selected", asset });

    const result = store.getState().analyzeSelectedApk();
    expect(store.getState().process).toEqual({ status: "uploading", asset });

    callbacks?.onPhaseChange?.("analysing");
    expect(store.getState().process).toEqual({ status: "analysing", asset });

    pending.resolve(assessment);
    await expect(result).resolves.toBe(true);
    expect(store.getState().process).toEqual({
      status: "success",
      asset,
      assessment,
    });
    expect(recordSuccessfulScan).toHaveBeenCalledTimes(1);
    expect(recordSuccessfulScan).toHaveBeenCalledWith(assessment, asset.name);
  });

  it("keeps the selected file and exposes no fake result after an error, then retries", async () => {
    const uploader = asUploader(
      jest
        .fn<Promise<ScanAssessment>, [UploadApkRequest, UploadApkCallbacks?]>()
        .mockRejectedValueOnce(new Error("Backend unavailable"))
        .mockResolvedValueOnce(assessment),
    );
    const recordSuccessfulScan = jest.fn().mockResolvedValue(true);
    const store = createScanStore({ uploadApk: uploader, recordSuccessfulScan });
    store.getState().selectApk(asset);

    await expect(store.getState().analyzeSelectedApk()).resolves.toBe(false);
    expect(store.getState().process).toEqual({
      status: "error",
      asset,
      message: "Backend unavailable",
    });
    expect("assessment" in store.getState().process).toBe(false);

    const retry = store.getState().analyzeSelectedApk();
    expect(store.getState().process).toEqual({ status: "uploading", asset });
    await expect(retry).resolves.toBe(true);
    expect(store.getState().process).toEqual({
      status: "success",
      asset,
      assessment,
    });
    expect(uploader).toHaveBeenCalledTimes(2);
    expect(recordSuccessfulScan).toHaveBeenCalledTimes(1);
  });

  it("prevents a second submission while an upload is active", async () => {
    const pending = deferred<ScanAssessment>();
    const uploader = asUploader(() => pending.promise);
    const store = createScanStore({ uploadApk: uploader });
    store.getState().selectApk(asset);

    const first = store.getState().analyzeSelectedApk();
    await expect(store.getState().analyzeSelectedApk()).resolves.toBe(false);
    expect(uploader).toHaveBeenCalledTimes(1);
    expect(store.getState().process.status).toBe("uploading");

    pending.resolve(assessment);
    await expect(first).resolves.toBe(true);
  });

  it("ignores a stale completion after reset", async () => {
    const pending = deferred<ScanAssessment>();
    const recordSuccessfulScan = jest.fn().mockResolvedValue(true);
    const store = createScanStore({
      uploadApk: asUploader(() => pending.promise),
      recordSuccessfulScan,
    });
    store.getState().selectApk(asset);

    const result = store.getState().analyzeSelectedApk();
    store.getState().reset();
    expect(store.getState().process).toEqual({ status: "idle" });

    pending.resolve(assessment);
    await expect(result).resolves.toBe(false);
    expect(store.getState().process).toEqual({ status: "idle" });
    expect(recordSuccessfulScan).not.toHaveBeenCalled();
  });

  it("keeps a valid scan successful when local history storage fails", async () => {
    const recordSuccessfulScan = jest
      .fn()
      .mockRejectedValue(new Error("Local storage unavailable"));
    const store = createScanStore({
      uploadApk: asUploader(async () => assessment),
      recordSuccessfulScan,
    });
    store.getState().selectApk(asset);

    await expect(store.getState().analyzeSelectedApk()).resolves.toBe(true);
    expect(store.getState().process).toEqual({
      status: "success",
      asset,
      assessment,
    });
    expect(recordSuccessfulScan).toHaveBeenCalledTimes(1);
  });
});
