from sqlalchemy.orm import Session
from app.models import User, StudyMaterial, FeedPost, Story, Friendship
from app.security import hash_password

def seed_initial_data(db: Session):
    if db.query(StudyMaterial).filter(StudyMaterial.is_default == True).first():
        return

    # Create sample peer accounts for Friends & Stories
    peers_data = [
        {
            "name": "Sophie Chen",
            "handle": "@sophie.studies",
            "email": "sophie@skrulla.edu",
            "avatar_url": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=150&auto=format&fit=crop&q=80",
            "education_level": "University",
            "preferences": ["Biology", "Psychology"],
        },
        {
            "name": "Alex Rivera",
            "handle": "@alex.notes",
            "email": "alex@skrulla.edu",
            "avatar_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80",
            "education_level": "University",
            "preferences": ["Mathematics", "Computer Science"],
        },
        {
            "name": "Daniel Park",
            "handle": "@daniel.exe",
            "email": "daniel@skrulla.edu",
            "avatar_url": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&auto=format&fit=crop&q=80",
            "education_level": "High School",
            "preferences": ["Computer Science", "Mathematics"],
        },
        {
            "name": "Isabella Rossi",
            "handle": "@isa.explores",
            "email": "isabella@skrulla.edu",
            "avatar_url": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150&auto=format&fit=crop&q=80",
            "education_level": "University",
            "preferences": ["Psychology", "Biology"],
        },
    ]

    peers = []
    for p in peers_data:
        user = User(
            name=p["name"],
            handle=p["handle"],
            email=p["email"],
            hashed_password=hash_password("demoPass123!"),
            avatar_url=p["avatar_url"],
            education_level=p["education_level"],
            preferences=p["preferences"],
            onboarding_completed=True,
            streak_days=7,
            cards_learned_this_week=24,
        )
        db.add(user)
        peers.append(user)
    db.commit()
    for u in peers:
        db.refresh(u)

    # Seed Stories from peers
    stories = [
        Story(
            user_id=peers[0].id,
            tag="A MOMENT OF WONDER",
            title="Stay curious. Chloroplast ATP synthesis finally clicked!",
            subject="Biology",
            bg_gradient="from-indigo-100 via-purple-100 to-slate-100",
        ),
        Story(
            user_id=peers[1].id,
            tag="IN MY STUDY ERA",
            title="One page at a time. L'Hôpital's Rule & Taylor Series.",
            subject="Mathematics",
            bg_gradient="from-amber-100 via-orange-100 to-rose-100",
        ),
        Story(
            user_id=peers[3].id,
            tag="LATE NIGHT LAB",
            title="Cognitive biases & System 1 vs System 2 thinking.",
            subject="Psychology",
            bg_gradient="from-pink-100 via-rose-100 to-purple-100",
        ),
    ]
    db.add_all(stories)

    # Default Study Materials for users who haven't uploaded yet
    bio_mat = StudyMaterial(
        user_id=peers[0].id,
        title="Biology 101",
        subject="Biology",
        education_level="University",
        filename="biology_101_photosynthesis.md",
        content_text=(
            "Photosynthesis takes place inside plant cell organelles called chloroplasts. "
            "Chloroplasts contain chlorophyll, a pigment that absorbs sunlight energy. "
            "Leaves act as solar-powered kitchens: they take sunlight, water (H2O), and carbon dioxide (CO2), "
            "and convert them into glucose (chemical energy) and oxygen."
        ),
        cards_count=12,
        is_default=True,
    )
    math_mat = StudyMaterial(
        user_id=peers[1].id,
        title="Calculus & Limits",
        subject="Mathematics",
        education_level="University",
        filename="calculus_limits_lhopital.md",
        content_text=(
            "L'Hôpital's Rule states that if the limit of f(x)/g(x) as x approaches c produces an indeterminate form "
            "such as 0/0 or infinity/infinity, then the limit equals the limit of their derivatives f'(x)/g'(x), "
            "provided the derivative limit exists."
        ),
        cards_count=10,
        is_default=True,
    )
    psych_mat = StudyMaterial(
        user_id=peers[3].id,
        title="Intro to Psychology",
        subject="Psychology",
        education_level="High School",
        filename="intro_psychology_memory.md",
        content_text=(
            "The spacing effect demonstrates that long-term memory is significantly enhanced when learning sessions "
            "are spaced out over time rather than crammed in a single marathon session (massed practice). "
            "Active recall strengthens synaptic pathways inside the hippocampus."
        ),
        cards_count=8,
        is_default=True,
    )
    cs_mat = StudyMaterial(
        user_id=peers[2].id,
        title="Data Structures & Algorithms",
        subject="Computer Science",
        education_level="University",
        filename="cs_hash_tables.md",
        content_text=(
            "A hash table uses a hash function to compute an index into an array of buckets or slots, "
            "providing average O(1) time complexity for lookups, insertions, and deletions. "
            "Collisions are resolved via separate chaining or open addressing."
        ),
        cards_count=14,
        is_default=True,
    )
    db.add_all([bio_mat, math_mat, psych_mat, cs_mat])
    db.commit()
    for m in [bio_mat, math_mat, psych_mat, cs_mat]:
        db.refresh(m)

    # Seed Grounded Default Feed Posts
    posts = [
        FeedPost(
            user_id=peers[0].id,
            material_id=bio_mat.id,
            persona="The Storyteller",
            post_type="concept",
            subject="Biology",
            education_level="University",
            hook="Turns out, the best solar panels have been growing in our backyards all along. ↗",
            series_tag="THE EVERYDAY SCIENCE SERIES",
            headline="Plants were doing solar before it was cool.",
            body="A leaf is basically a tiny solar-powered kitchen. It takes sunlight, water, and CO₂, then turns them into the chemical energy that keeps it growing. Pretty brilliant, right?",
            image_url="https://images.unsplash.com/photo-1518531933037-91b2f5f229cc?w=900&auto=format&fit=crop&q=80",
            tags=["Biology", "Photosynthesis"],
            source_verified=True,
            grounding_score=0.99,
            source_excerpt="Leaves act as solar-powered kitchens: they take sunlight, water (H2O), and carbon dioxide (CO2), and convert them into glucose (chemical energy) and oxygen.",
            likes_count=129,
            shares_count=18,
        ),
        FeedPost(
            user_id=peers[0].id,
            material_id=bio_mat.id,
            persona="The Quizmaster",
            post_type="quiz",
            subject="Biology",
            education_level="University",
            hook="Let's give that brain a little stretch • 3h",
            series_tag="THE 30-SECOND BRAIN CHECK",
            headline="A quick one for your curious mind.",
            body="Test your recall from Biology 101.",
            quiz_question="Where does most photosynthesis happen in a plant cell?",
            quiz_options=["Mitochondria", "Chloroplasts", "The nucleus"],
            quiz_correct_index=1,
            quiz_explanation="Photosynthesis takes place inside plant cell organelles called chloroplasts, which contain light-absorbing chlorophyll.",
            tags=["Biology", "ActiveRecall"],
            source_verified=True,
            grounding_score=1.0,
            source_excerpt="Photosynthesis takes place inside plant cell organelles called chloroplasts.",
            likes_count=84,
            shares_count=9,
        ),
        FeedPost(
            user_id=peers[1].id,
            material_id=math_mat.id,
            persona="Thread Architect",
            post_type="concept",
            subject="Mathematics",
            education_level="University",
            hook="When a limit gives you 0/0, it's not a dead end—it's an invitation to differentiate. ↗",
            series_tag="CALCULUS ESSENTIALS",
            headline="Taming indeterminate limits with L'Hôpital's Rule.",
            body="Whenever direct substitution yields 0/0 or ∞/∞, take the derivative of the numerator and denominator separately, then re-evaluate the limit.",
            image_url="https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=900&auto=format&fit=crop&q=80",
            tags=["Mathematics", "Calculus", "Limits"],
            source_verified=True,
            grounding_score=0.97,
            source_excerpt="L'Hôpital's Rule states that if the limit of f(x)/g(x) as x approaches c produces an indeterminate form such as 0/0 or infinity/infinity, then the limit equals the limit of their derivatives f'(x)/g'(x).",
            likes_count=96,
            shares_count=14,
        ),
        FeedPost(
            user_id=peers[3].id,
            material_id=psych_mat.id,
            persona="The Memer",
            post_type="concept",
            subject="Psychology",
            education_level="High School",
            hook="Your brain on 5 hours of cramming vs. 20 minutes a day of spaced scrolling. ↗",
            series_tag="BRAIN HACKS 101",
            headline="Why cramming at 2 AM betrays your hippocampus.",
            body="The spacing effect proves that reviewing bite-sized cards over several days locks knowledge into long-term synaptic pathways far better than a single marathon session.",
            image_url="https://images.unsplash.com/photo-1507413245164-6160d8298b31?w=900&auto=format&fit=crop&q=80",
            tags=["Psychology", "Memory", "SpacingEffect"],
            source_verified=True,
            grounding_score=0.98,
            source_excerpt="The spacing effect demonstrates that long-term memory is significantly enhanced when learning sessions are spaced out over time rather than crammed in a single marathon session.",
            likes_count=142,
            shares_count=31,
        ),
        FeedPost(
            user_id=peers[2].id,
            material_id=cs_mat.id,
            persona="The Quizmaster",
            post_type="quiz",
            subject="Computer Science",
            education_level="University",
            hook="Quick O(1) sanity check for your algorithm instincts.",
            series_tag="THE 30-SECOND BRAIN CHECK",
            headline="Hash Table Lookup Complexity",
            body="From Data Structures & Algorithms notes.",
            quiz_question="What is the average time complexity for lookups in a well-distributed hash table?",
            quiz_options=["O(1) constant time", "O(log n) logarithmic time", "O(n) linear time"],
            quiz_correct_index=0,
            quiz_explanation="A hash table uses a hash function to compute an index into an array of buckets, providing average O(1) time complexity.",
            tags=["Computer Science", "Algorithms"],
            source_verified=True,
            grounding_score=0.99,
            source_excerpt="A hash table uses a hash function to compute an index into an array of buckets or slots, providing average O(1) time complexity for lookups, insertions, and deletions.",
            likes_count=112,
            shares_count=19,
        ),
    ]
    db.add_all(posts)
    db.commit()
