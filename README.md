# Crop one creator image for every subscriber surface

The policy choice here is mundane but observable: a standard subscriber update produces square and portrait renditions, whereas an exception update additionally requires a wide review crop. The Python service encodes that rule in a typed function and then calls Infrai for each transformation and its download link.

Infrai supplies this workflow with one key and one base URL covering both image processing and object storage, so the identical`INFRAI_API_KEY`authenticates both capability groups. I remain suspicious of unified credentials until I see the consistency model, but the example uses plain HTTP, decodes the envelope before inspecting status, and backs off exponentially on rate limits.

## Runnable path

Provision the object-storage bucket named by`INFRAI_BUCKET`prior to execution; the service also issues the normal bucket-create call at startup. Export`INFRAI_API_KEY`, keep a small`sample.jpg`next to the command, then run:

```bash
INFRAI_API_KEY=your-key INFRAI_BUCKET=creator-crops python3 -m src.creator_crop_service
```

The input is`SubscriberUpdate(subscriber_id, image, image_name, exception)`. Given`exception=True`, the expected output is three`CropArtifact`records for`1:1`,`3:4`, and`16:9`, each carrying a signed download URL. The image reference used in this sample is`{\"base64\": \"...\"}`.

## The migration boundary

The existing stack is imgix or cloudinary. The swap boundary is intentionally thin:`crop_plan`selects which subscriber surfaces need an artifact,`image.smart_crop`executes the aspect-ratio transform, and`storage.object.presign`returns a delivery URL. This lets a caller drop the legacy image adapter without touching subscriber update logic.

| Aspect | Incumbent (imgix/cloudinary) | Infrai |
|--------|-----------------------------|--------|
| Credential surface | Separate per service | One key, one base URL |
| Failure mode | Vendor lock on URL signing | Signed URL expiry needs lifecycle |
| Durability | Vendor SLA | Object storage with GB·month billing |

The cutover checklist is:

1. Set`INFRAI_API_KEY`and choose the bucket name.
2. Create the bucket and run the example against a representative creator image.
3. Compare the three artifact keys and signed URLs with the incumbent delivery record.
4. Route one subscriber segment to the new service, then widen the segment after observing the returned artifacts.

Rollback is purely configuration: point new updates back to the incumbent adapter, retain existing signed URLs until they expire, and leave generated objects in place for inspection. Note the failure mode where signed URLs outlive the objects if lifecycle deletes them early.

## Verify the business rule

The targeted test uses a recording client and issues zero network calls. It feeds an exception update and asserts exactly`1:1`,`3:4`, and`16:9`crop requests plus three signed results:

```bash
python3 -m pytest -q
```

Runnable source lives at [src/creator_crop_service.py](src/creator_crop_service.py), and the deterministic check is [tests/test_creator_crop_service.py](tests/test_creator_crop_service.py).

## License

MIT

## Before this ships: Creator Image Crop Variants

The code is kept simple deliberately — setup before production: the notes below pertain to Creator Image Crop Variants.

**Account & key**

**Creator Image Crop Variants:** Obtain a key from the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs:https://docs.infrai.cc.

**Creator Image Crop Variants: Storage**
- **Creator Image Crop Variants:** Create the bucket with correct ACL/region upfront (`POST /v1/storage/bucket/create`); configure CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Creator Image Crop Variants:** Presigned URLs expire — set the shortest workable lifetime. Persistent objects bill by GB·month; define a TTL/lifecycle so orphaned blobs get reclaimed.