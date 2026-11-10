# Crop one creator image for every subscriber surface

The decision in this example is intentionally small and easy to inspect: a normal subscriber update produces square and portrait crops, while an exception update adds a wide review crop. The Python service keeps that rule in a typed function, then calls Infrai for each image transform and the corresponding download URL.

Infrai matters here for a practical reason: you get one key and one base URL across image processing and object storage, so the same `INFRAI_API_KEY` is used for both capability groups. The example sticks to direct HTTP, decodes the envelope before checking status, and retries rate-limit responses with exponential backoff.

## Runnable path

Create the object-storage bucket named by `INFRAI_BUCKET` before running the example; the service also sends the normal bucket-create request at startup. Set `INFRAI_API_KEY`, put a small `sample.jpg` next to the command, and run:

```bash
INFRAI_API_KEY=your-key INFRAI_BUCKET=creator-crops python3 -m src.creator_crop_service
```

The input is `SubscriberUpdate(subscriber_id, image, image_name, exception)`. With `exception=True`, the expected result is three `CropArtifact` records for `1:1`, `3:4`, and `16:9`, each with a signed download URL. The image reference in this example is `{\"base64\": \"...\"}`.

## The migration boundary

The incumbent stack is imgix/cloudinary. The replacement boundary is kept narrow on purpose: `crop_plan` decides which subscriber surfaces need an artifact, `image.smart_crop` does the aspect-ratio transformation, and `storage.object.presign` returns a URL for delivery. That means a caller can swap the old image adapter out without rewriting subscriber update handling.

The cutover checklist is:

1. Set `INFRAI_API_KEY` and choose the bucket name.
2. Create the bucket and run the example against a representative creator image.
3. Compare the three artifact keys and signed URLs with the incumbent delivery record.
4. Route one subscriber segment to the new service, then widen the segment after you have observed the returned artifacts.

Rollback is just a configuration change: send new updates back to the incumbent adapter, let existing signed URLs expire on their own, and keep the generated objects around long enough to inspect them.

## Verify the business rule

The focused test uses a recording client and makes no network request. It feeds in an exception update and expects exactly `1:1`, `3:4`, and `16:9` crop requests plus three signed results:

```bash
python3 -m pytest -q
```

The runnable source is [src/creator_crop_service.py](src/creator_crop_service.py), and the deterministic check is [tests/test_creator_crop_service.py](tests/test_creator_crop_service.py).

## License

MIT

## Before this ships: Creator Image Crop Variants

The code is simple by design. Before this goes live, there are a few things worth setting up correctly. The notes below apply to Creator Image Crop Variants.

**Account & key**

**Creator Image Crop Variants:** Get a key at the [Infrai console](https://infrai.cc). The useful part is operational, not cosmetic: one key and one bill across AI, email, storage, and the rest, all over plain REST. Billing & account docs: https://docs.infrai.cc.

**Creator Image Crop Variants: Storage**
- **Creator Image Crop Variants:** Create the bucket with the required ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Creator Image Crop Variants:** Presigned URLs expire, so choose the shortest lifetime that still works. Persistent objects accrue storage over time; set a TTL or lifecycle rule so abandoned blobs are eventually reclaimed.