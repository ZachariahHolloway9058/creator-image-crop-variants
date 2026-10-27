import unittest

from src.creator_crop_service import SubscriberUpdate, crop_plan, process_update


class RecordingClient:
    def __init__(self):
        self.calls = []

    def request(self, method, path, body):
        self.calls.append((method, path, body))
        if path == "/v1/image/smart_crop":
            return {"ok": True, "data": {"key": "processed.jpg"}, "error": None, "metadata": {}}
        return {"ok": True, "data": {"url": "https://signed.example/crop"}, "error": None, "metadata": {}}


class CropDecisionTest(unittest.TestCase):
    def test_exception_update_adds_wide_review_variant_and_signs_each_result(self):
        update = SubscriberUpdate("reader-7", {"base64": "aW1hZ2U="}, "portrait.jpg", exception=True)
        self.assertEqual(crop_plan(update), ("1:1", "3:4", "16:9"))

        client = RecordingClient()
        artifacts = process_update(client, update, "creator-crops")

        crop_calls = [call for call in client.calls if call[1] == "/v1/image/smart_crop"]
        self.assertEqual([call[2]["aspect"] for call in crop_calls], ["1:1", "3:4", "16:9"])
        self.assertEqual(len(artifacts), 3)
        self.assertTrue(all(artifact.download_url.startswith("https://") for artifact in artifacts))


if __name__ == "__main__":
    unittest.main()
