# Review Systems Guide
# Multi-layered review system for OCR corrections.

## Components

### 1. Expert Review Quota (quota_manager.py)
Weekly review quotas per expert level. Blind random sampling (10%).
Progressive: junior=10, senior=50, admin=unlimited.

### 2. Double Blind Review (double_blind_reviewer.py)
For sensitive documents (medical, legal, financial).
Two independent reviewers, identities hidden.
Inter-reviewer agreement scoring.

### 3. Voting Tracker (voting_tracker.py)
Majority voting for character-level corrections.
Time-weighted and confidence-weighted voting.

### 4. User Manager (user_manager.py)
Role-based access: viewer, reviewer, senior, admin.
Expert badge system based on review accuracy.

### 5. Arabic NLP Utils (arabic_nlp_utils.py)
Diacritics normalization, Alef/Hamza unification.
RTL-aware similarity scoring.

### 6. Review Dashboard (review_dashboard.py)
Gradio-based UI for batch review and comparison.
