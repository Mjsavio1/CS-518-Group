# Monolithic Architecture Diagram

```mermaid
graph TD
    User[User / Mobile or Web App]

    subgraph Monolith["Monolithic Backend Application"]
        Auth[Authentication & Account Service]
        Spotify[Spotify Integration Service]
        Analysis[Listening Analysis Service]
        Discovery[Artist Discovery & Recommendation Service]
        Metadata[Artist Metadata Service]
        Feedback[User Preference & Feedback Service]
        Explain[Transparency & Explanation Service]
        Notify[Notification / Delivery Service]
    end

    SpotifyAPI[(Spotify Web API)]
    Database[(Application Database)]

    User -->|Login / Use App| Auth
    User -->|View Recommendations| Discovery
    User -->|Like / Skip| Feedback
    User -->|View Artist Profiles| Metadata

    Auth --> Spotify
    Spotify --> SpotifyAPI
    Spotify --> Analysis
    Analysis --> Discovery
    Discovery --> Metadata
    Discovery --> Explain
    Feedback --> Discovery
    Discovery --> Notify

    Auth --> Database
    Analysis --> Database
    Discovery --> Database
    Metadata --> Database
    Feedback --> Database
    Notify --> Database
