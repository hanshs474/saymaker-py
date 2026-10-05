import os
import unittest

import saymaker


def fake(calls, final):
    def t(method, url, body, headers):
        calls.append((method, url, body, headers))
        if url.endswith("/api/ai/generate"):
            return {"code": 0, "data": {"id": "row1"}}
        return {"code": 0, "data": final}

    return t


class SayMakerTests(unittest.TestCase):
    def setUp(self):
        os.environ.pop("SAYMAKER_API_KEY", None)

    def test_validates(self):
        with self.assertRaises(ValueError):
            saymaker.generate("  ", api_key="sk-x")
        with self.assertRaises(ValueError):
            saymaker.generate("x", image_url="file:///x.png", api_key="sk-x")

    def test_needs_a_key(self):
        with self.assertRaises(saymaker.AuthError):
            saymaker.generate("x")

    def test_wall_is_a_200(self):
        with self.assertRaises(saymaker.AuthError):
            saymaker._parse_submit({"code": 0, "data": {"wall": True, "reason": "sign_in_required"}})

    def test_refusals(self):
        with self.assertRaises(saymaker.AuthError):
            saymaker._parse_submit({"code": -1, "message": "invalid API key"})
        with self.assertRaises(saymaker.QuotaError):
            saymaker._parse_submit({"code": -1, "message": "insufficient credits"})

    def test_image_prefers_clean_and_polls_query(self):
        calls = []
        final = {"status": "success", "images": ["https://cdn/m.webp"], "cleanImages": ["https://cdn/c.webp"]}
        url = saymaker.generate("x", api_key="sk-abc", poll_every=0, base_url="https://t", transport=fake(calls, final))
        self.assertEqual(url, "https://cdn/c.webp")
        self.assertEqual(calls[0][3], {"Authorization": "Bearer sk-abc"})
        self.assertEqual(calls[0][2]["model"], "saymaker-image-v1")
        self.assertEqual(calls[0][2]["provider"], "kie")
        self.assertEqual(calls[1][:3], ("POST", "https://t/api/ai/query", {"taskId": "row1"}))

    def test_edit_sends_image_input(self):
        calls = []
        final = {"status": "success", "images": ["https://cdn/x.webp"]}
        saymaker.generate("short hair", image_url="https://x/p.jpg", api_key="sk", poll_every=0, base_url="https://t", transport=fake(calls, final))
        body = calls[0][2]
        self.assertEqual(body["scene"], "image-to-image")
        self.assertEqual(body["model"], "nano-banana-2-lite")
        self.assertEqual(body["options"]["image_input"], ["https://x/p.jpg"])
        self.assertEqual(body["options"]["size"], "auto")

    def test_video_routes_by_model(self):
        calls = []
        final = {"status": "success", "videos": ["https://cdn/v.mp4"]}
        url = saymaker.generate_video("a boat", api_key="sk", duration=6, poll_every=0, base_url="https://t", transport=fake(calls, final))
        self.assertEqual(url, "https://cdn/v.mp4")
        body = calls[0][2]
        self.assertEqual((body["mediaType"], body["scene"], body["model"], body["provider"]), ("video", "text-to-video", "minimax-h3-fast", "vgenv"))
        self.assertEqual(body["options"]["duration"], 6)

    def test_failed_run(self):
        with self.assertRaises(saymaker.RejectedError):
            saymaker.generate("x", api_key="sk", poll_every=0, transport=fake([], {"status": "failed"}))


if __name__ == "__main__":
    unittest.main()
