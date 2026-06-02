"""Deterministic content generation for cookbook exercises."""

from __future__ import annotations

from .models import CampaignBrief, PostDraft


PLATFORM_LIMITS = {
    "linkedin": 700,
    "x": 280,
    "threads": 500,
}


HOOKS = [
    "Your meeting notes should become decisions, not archaeology.",
    "Product teams lose momentum when context lives in five places.",
    "A good product note answers: what changed, why, and what happens next.",
    "Launch week is easier when customer insights are already organized.",
]


def generate_posts(brief: CampaignBrief, *, platforms: list[str], count: int) -> list[PostDraft]:
    if count < 1:
        raise ValueError("count must be at least 1")
    if not platforms:
        raise ValueError("platforms must include at least one platform")

    drafts: list[PostDraft] = []
    for index in range(count):
        platform = platforms[index % len(platforms)]
        drafts.append(_draft_for_platform(brief, platform=platform, index=index))
    return drafts


def _draft_for_platform(brief: CampaignBrief, *, platform: str, index: int) -> PostDraft:
    if platform not in PLATFORM_LIMITS:
        raise ValueError(f"Unsupported platform: {platform}")

    feature = brief.features[index % len(brief.features)]
    goal = brief.goals[index % len(brief.goals)]
    hook = HOOKS[index % len(HOOKS)]
    hashtags = " ".join(brief.hashtags[:2])

    if platform == "x":
        body = (
            f"{brief.brand}: {feature} for {brief.audience}. "
            f"{brief.call_to_action}. {hashtags}"
        )
    else:
        body = (
            f"{hook}\n\n"
            f"{brief.brand} helps {brief.audience} with {feature}, so teams can {goal}.\n\n"
            f"{brief.call_to_action}. {hashtags}"
        )

    limit = PLATFORM_LIMITS[platform]
    if len(body) > limit:
        body = body[: limit - 1].rstrip() + "…"

    return PostDraft(
        id=f"draft-{index + 1:03d}",
        platform=platform,
        text=body,
        campaign=brief.campaign,
    )
