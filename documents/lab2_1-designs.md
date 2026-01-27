1️⃣ Envisioned Services (High-Level Architecture)

Your app naturally fits a service-oriented / microservice-style breakdown, even if you implement it as modular services inside one backend at first.

Core Services Overview

Authentication & Account Service

Spotify Integration Service

Listening Analysis Service

Artist Discovery & Recommendation Service

Artist Metadata Service

User Preference & Feedback Service

Transparency & Explanation Service

Notification / Delivery Service (optional for MVP)

2️⃣ Services Mapped to Epics
Epic	Related Service(s)
Spotify Integration & Authentication	Auth Service, Spotify Integration Service
Listening Data Analysis	Listening Analysis Service
Artist Discovery & Recommendation	Discovery & Recommendation Service
Artist Profiles & Exploration	Artist Metadata Service
User Interaction & Feedback Loop	User Preference & Feedback Service
Ethical Discovery & Transparency	Transparency & Explanation Service
3️⃣ Services + Business Logic Examples

Below is the important part: what business logic actually lives inside each service.

🔐 1. Authentication & Account Service

Responsibility

Manage users and sessions

Handle OAuth state and app accounts

Business Logic Examples

Determine whether a user is new or returning

Enforce account linking rules (1 Spotify account per user)

Handle token refresh logic and expiration

Decide when re-authentication is required

📌 Not business logic: Spotify’s OAuth itself (that’s Spotify’s job)

🎧 2. Spotify Integration Service

Responsibility

Communicate with Spotify’s API

Normalize Spotify data into your internal format

Business Logic Examples

Decide which Spotify endpoints to call (recent tracks vs top tracks)

Apply rate-limit handling and retries

Filter out private sessions or invalid data

Cache Spotify responses to reduce API calls

Decide refresh cadence (e.g., pull new data every 24 hours)

📌 Key point: This service does not decide recommendations—it only fetches data.

📊 3. Listening Analysis Service

Responsibility

Convert raw listening data into usable insights

Business Logic Examples

Determine a user’s dominant genres

Compute artist affinity scores

Detect listening “moods” (tempo, energy, valence)

Weight recent listens more heavily than old listens

Ignore outliers (e.g., a one-time podcast or random genre)

📌 This is where “taste” becomes structured data.

🔍 4. Artist Discovery & Recommendation Service

Responsibility

Match users with smaller artists they’re likely to enjoy

Business Logic Examples

Define what qualifies as a “small artist” (popularity threshold)

Exclude artists the user already follows

Rank candidate artists by similarity score

Balance familiarity vs discovery (e.g., 70% similar / 30% novel)

Prevent repeat recommendations too frequently

Enforce diversity rules (don’t show 10 artists from same genre)

📌 This is your core competitive advantage.

🎤 5. Artist Metadata Service

Responsibility

Provide enriched artist profiles

Business Logic Examples

Merge Spotify artist data with external sources (Bandcamp, socials)

Decide which metrics to show (followers, popularity, genre tags)

Detect if an artist is “claimed” or verified (future feature)

Cache artist data for performance

📌 This service turns raw artists into compelling stories.

👍 6. User Preference & Feedback Service

Responsibility

Learn from user behavior

Business Logic Examples

Interpret likes, skips, saves, follows

Adjust recommendation weights based on feedback

Detect strong dislikes vs neutral skips

Track long-term vs short-term preferences

Build a user “taste profile” that evolves over time

📌 This service closes the feedback loop.

🧠 7. Transparency & Explanation Service

Responsibility

Explain recommendations clearly and ethically

Business Logic Examples

Generate explanation templates:

“Recommended because you listen to X and Y”

Choose the most meaningful reason to show

Avoid misleading metrics

Limit explanation complexity for readability

Ensure explanations don’t leak private data

📌 This builds trust and differentiates you from opaque algorithms.

🔔 8. Notification / Delivery Service (Optional)

Responsibility

Deliver recommendations at the right time

Business Logic Examples

Decide when to send discovery drops

Avoid notification fatigue

Personalize delivery frequency

Respect user notification preferences

4️⃣ Summary: What Counts as Business Logic?

Business logic is anything that answers:

Who gets what?

When do they get it?

Why does this happen instead of something else?

For your app, business logic lives in:

Popularity thresholds

Similarity scoring

Weighting rules

Filtering decisions

Feedback interpretation

Ethical discovery constraints