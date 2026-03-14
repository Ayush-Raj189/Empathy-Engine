"""
samples.py
----------
Curated demo text samples for each emotion category.
Used by the Streamlit UI as quick-start examples.
"""

from dataclasses import dataclass


@dataclass
class TextSample:
    label: str
    text: str
    expected_emotion: str
    description: str


SAMPLES: list[TextSample] = [
    TextSample(
        label="🎉 Excited Announcement",
        text=(
            "We just got the contract!! This is AMAZING — I can't believe it! "
            "After months of hard work, we finally made it. "
            "The team is going to be absolutely thrilled when they hear this news. "
            "Best day ever!!!"
        ),
        expected_emotion="excitement",
        description="High-intensity excitement with capitalisation and multiple exclamation marks.",
    ),
    TextSample(
        label="😊 Warm Welcome",
        text=(
            "Good morning! It's so wonderful to have you here today. "
            "We're really happy to help you with anything you need. "
            "Please don't hesitate to ask — we love making your experience great."
        ),
        expected_emotion="joy",
        description="Warm, positive tone typical of a friendly customer service opening.",
    ),
    TextSample(
        label="🙏 Genuine Gratitude",
        text=(
            "I just wanted to take a moment to say thank you so much. "
            "Your support has meant the world to me during this time. "
            "I am truly grateful for everything you've done."
        ),
        expected_emotion="gratitude",
        description="Heartfelt thankfulness with measured, sincere delivery.",
    ),
    TextSample(
        label="😐 Neutral Update",
        text=(
            "Your order has been processed and will be shipped within 3 to 5 business days. "
            "You will receive a confirmation email shortly. "
            "Please contact support if you have any questions."
        ),
        expected_emotion="neutral",
        description="Standard transactional message — no emotional colouring.",
    ),
    TextSample(
        label="😢 Disappointed Customer",
        text=(
            "I'm really disappointed with my recent experience. "
            "I waited three weeks for my order and it still hasn't arrived. "
            "I'm feeling quite let down and I'm not sure I'll order again."
        ),
        expected_emotion="sadness",
        description="Mild sadness and disappointment — slower, lower, softer delivery.",
    ),
    TextSample(
        label="😤 Frustrated User",
        text=(
            "This is the third time I've contacted support about the SAME issue. "
            "Nothing has been fixed. The app crashes every single time I try to log in. "
            "This is completely unacceptable. I need this resolved TODAY."
        ),
        expected_emotion="frustration",
        description="Escalating frustration — faster, clipped, louder delivery.",
    ),
    TextSample(
        label="😠 Angry Complaint",
        text=(
            "I am absolutely furious. You charged my card TWICE and nobody has responded "
            "to my emails for two weeks. This is outrageous behaviour. "
            "I want a full refund immediately or I will be filing a formal complaint."
        ),
        expected_emotion="anger",
        description="High-intensity anger — fast, forceful, maximum emphasis.",
    ),
    TextSample(
        label="😨 Worried Inquiry",
        text=(
            "I'm a little worried about my account. I received an email saying "
            "there was unusual activity and I'm not sure what to do. "
            "Could you please help me? I don't want anything bad to happen."
        ),
        expected_emotion="fear",
        description="Anxious, tentative pacing with lower volume.",
    ),
    TextSample(
        label="😲 Surprised Reaction",
        text=(
            "Wait, what?! You're telling me the deadline was moved to tomorrow? "
            "I had no idea — nobody told me! "
            "I can't believe this. How is that even possible?"
        ),
        expected_emotion="surprise",
        description="Sudden surprise — sharp uptick in rate and pitch.",
    ),
    TextSample(
        label="🤔 Curious Question",
        text=(
            "I was wondering — how exactly does the recommendation engine decide "
            "which products to show me? I'd love to understand the logic behind it. "
            "Does it learn from my past purchases, or is there something else going on?"
        ),
        expected_emotion="curiosity",
        description="Inquisitive, exploratory tone — slightly slower, rising inflection.",
    ),
]


def get_sample_by_emotion(emotion: str) -> TextSample | None:
    """Return the first sample matching the given emotion."""
    for s in SAMPLES:
        if s.expected_emotion == emotion:
            return s
    return None


def get_all_labels() -> list[str]:
    return [s.label for s in SAMPLES]
