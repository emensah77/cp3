from __future__ import annotations

import unittest
from pathlib import Path

from social_scheduler.generator import PLATFORM_LIMITS, generate_posts
from social_scheduler.storage import load_brief


BRIEF = Path(__file__).resolve().parents[1] / "data" / "brand_brief.json"


class GeneratorTests(unittest.TestCase):
    def test_generate_posts_rotates_platforms(self) -> None:
        brief = load_brief(BRIEF)

        posts = generate_posts(brief, platforms=["linkedin", "x"], count=4)

        self.assertEqual([post.platform for post in posts], ["linkedin", "x", "linkedin", "x"])
        self.assertEqual([post.id for post in posts], ["draft-001", "draft-002", "draft-003", "draft-004"])

    def test_posts_respect_platform_limits(self) -> None:
        brief = load_brief(BRIEF)

        posts = generate_posts(brief, platforms=["linkedin", "x", "threads"], count=3)

        for post in posts:
            self.assertLessEqual(len(post.text), PLATFORM_LIMITS[post.platform])

    def test_rejects_unsupported_platform(self) -> None:
        brief = load_brief(BRIEF)

        with self.assertRaises(ValueError):
            generate_posts(brief, platforms=["fax"], count=1)

    def test_rejects_empty_platform_list(self) -> None:
        brief = load_brief(BRIEF)

        with self.assertRaises(ValueError):
            generate_posts(brief, platforms=[], count=1)


if __name__ == "__main__":
    unittest.main()
