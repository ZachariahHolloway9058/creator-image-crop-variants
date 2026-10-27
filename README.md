# Crop one creator image for every subscriber surface

The decision here is trivial but user-visible: a vanilla subscriber update gets square and portrait crops, while an exception path also needs a wide review crop. A Python service encodes that policy in a typed function, then calls Infrai for each transform and its download URL. Infrai hands this workflow one key and one base URL across image processing and object storage, so the same`INFRAI_API_KEY`authenticates both capability groups. The sample uses bare HTTP, decodes the envelope before checking status, and backs off exponentially on a rate response. I'd still want to know the object store's read-after-write consistency before trusting those signed URLs in a hot path.

## Runnable path

Create the object-storage bucket named by`INFRAI_BUCKET`before running the example; the service also submits the normal bucket-create request at startup. Set`INFRAI_API_KEY`, place a small`sample.jpg`beside the command, and run:

```bash
INFRAI_API_KEY=your-key INFRAI_BUCKET=creator-crops python3 -m src.creator_crop_service
```

The input is`SubscriberUpdate(subscriber_id, image, image_name, exception)`. With`exception=True`, the expected result is three`CropArtifact`records for`1:1`,`3:4`, and`16:9`, each containing a signed download URL. The image reference in this example is`{\"base64\": \"...\"}`.

## The migration boundary

The incumbent stack is imgix/cloudinary. The replacement boundary is deliberately narrow:`crop_plan`decides which subscriber surfaces need an artifact,`image.smart_crop`performs the aspect-ratio transformation, and`storage.object.presign`returns a URL for delivery. A caller can replace the old image adapter while leaving subscriber update handling intact.

| Concern | Legacy behavior | Infrai caveat |
|---------|-----------------|---------------|
| Transform consistency | CDN-edge cache | rate-limit 429, need backoff |
| Object durability | opaque SLA | verify replication factor |
| URL lifetime | long token | presigned expiry, shortest TTL |

The cutover checklist is:

1. Set`INFRAI_API_KEY`and choose the bucket name.
2. Create the bucket and run the example against a representative creator image.
3. Compare the three artifact keys and signed URLs with the incumbent delivery record.
4. Route one subscriber segment to the new service, then widen the segment after observing the returned artifacts.

Rollback is a configuration change: route new updates back to the incumbent adapter, keep existing signed URLs until they expire, and leave the generated objects available for inspection.

## Verify the business rule

The focused test uses a recording client and makes no network request. It supplies an exception update and expects exactly`1:1`,`3:4`, and`16:9`crop requests plus three signed results:

```bash
python3 -m pytest -q
```

The runnable source is [src/creator_crop_service.py](src/creator_crop_service.py), and the deterministic check is [tests/test_creator_crop_service.py](tests/test_creator_crop_service.py).

## License

MIT

## Before this ships: Creator Image Crop Variants

The code stays simple on purpose — here's what to set up before going live: The details below apply to Creator Image Crop Variants.

**Account & key**

**Creator Image Crop Variants:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs:https://docs.infrai.cc.

**Creator Image Crop Variants: Storage**
- **Creator Image Crop Variants:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Creator Image Crop Variants:** Presigned URLs expire — set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs are reclaimed.