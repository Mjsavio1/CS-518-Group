# Entity Relationship Diagram

[![](https://mermaid.ink/img/pako:eNqNU12v0zAM_SuRn9up7dYuN298iBdAQny8oEhTaL0uWpNUSQqMrv-dpHe7sN2B9pLasY_PsVOPUJsGgUGaplzXRm9ly7gmpBMHM3hGsNtzPQfRvpaitUJxzX0jLdZeGk0-v4z-F4eWjNHi3nkrdUu0UEgIBw7hnAN6UN9C2hByN7IhH95eRE-wXjj3w9jmJtT1xsvtIaLf_I2ewhE-n07hF3VtBu3Pgp6Dr6ivhN0q_U46jzoI3OyCZWwo41FdtexMiCv0ohFeXDYQbpDgd9R-M5t38_-RH4v_Q91HDB0r1KF0fJO7Vd1ROr7s8Zimx_FquoxDJ_XeBcTz0UeEGW8PLQCl6o31J-iZ4T_53RxwxJtHyO3EaZZ5OYtIprfGqkAGCbRWNsC8HTABhVaJ6MIY_3gOfocKObBgNsLuI9UUML3QX41RZ5g1Q7sDthWdC97Qx-c8bcZTSmBH-yoOAtjDXAHYCD-BFeUiz3K6zFfLKi_XRbFO4ACMFgtKH2hVZFVWripKpwR-zZzZYl3m5apYUkqzVbVeVglgI0PP7x8Xd97f6Te9EFH3?type=png)](https://mermaid.live/edit#pako:eNqNU12v0zAM_SuRn9up7dYuN298iBdAQny8oEhTaL0uWpNUSQqMrv-dpHe7sN2B9pLasY_PsVOPUJsGgUGaplzXRm9ly7gmpBMHM3hGsNtzPQfRvpaitUJxzX0jLdZeGk0-v4z-F4eWjNHi3nkrdUu0UEgIBw7hnAN6UN9C2hByN7IhH95eRE-wXjj3w9jmJtT1xsvtIaLf_I2ewhE-n07hF3VtBu3Pgp6Dr6ivhN0q_U46jzoI3OyCZWwo41FdtexMiCv0ohFeXDYQbpDgd9R-M5t38_-RH4v_Q91HDB0r1KF0fJO7Vd1ROr7s8Zimx_FquoxDJ_XeBcTz0UeEGW8PLQCl6o31J-iZ4T_53RxwxJtHyO3EaZZ5OYtIprfGqkAGCbRWNsC8HTABhVaJ6MIY_3gOfocKObBgNsLuI9UUML3QX41RZ5g1Q7sDthWdC97Qx-c8bcZTSmBH-yoOAtjDXAHYCD-BFeUiz3K6zFfLKi_XRbFO4ACMFgtKH2hVZFVWripKpwR-zZzZYl3m5apYUkqzVbVeVglgI0PP7x8Xd97f6Te9EFH3)

## Entities

### User
Represents a user of the application.
- user_id (PK)
- email
- display_name
- created_at

### SpotifyAccount
Represents a connected Spotify account for a user.
- spotify_account_id (PK)
- spotify_user_id
- access_token
- refresh_token
- token_expiration
- user_id (FK)

### ListeningHistoryItem
Represents a song the user has listened to.
- history_item_id (PK)
- track_id
- artist_id
- listened_at
- spotify_account_id (FK)

### Recommendation
Represents a song or artist recommended to the user.
- recommendation_id (PK)
- track_id
- artist_id
- generated_at
- explanation
- user_id (FK)

## Relationships

- A User connects to exactly one SpotifyAccount.
- A SpotifyAccount contains many ListeningHistoryItems.
- Each ListeningHistoryItem belongs to one SpotifyAccount.
- A User can receive many Recommendations.
- Each Recommendation is generated for exactly one User.

Listening history data is analyzed to identify patterns in user preferences such as genre affinity and listening behavior. These insights are used to generate personalized recommendations, with an emphasis on smaller or emerging artists.
