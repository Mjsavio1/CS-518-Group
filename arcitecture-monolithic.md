# Modular Monolithic Architecture Diagram

```mermaid
graph TD
    User[User / Client App]

    %% Controller Layer
    subgraph Controllers["Controller Layer"]
        AuthController[Auth Controller]
        DiscoveryController[Discovery Controller]
        ArtistController[Artist Controller]
        FeedbackController[Feedback Controller]
    end

    %% Service Layer
    subgraph Services["Service Layer (Business Logic)"]
        AuthService[Authentication & Account Service]
        SpotifyService[Spotify Integration Service]
        AnalysisService[Listening Analysis Service]
        DiscoveryService[Artist Discovery & Recommendation Service]
        MetadataService[Artist Metadata Service]
        FeedbackService[User Preference & Feedback Service]
        ExplainService[Transparency & Explanation Service]
        NotificationService[Notification Service]
    end

    %% Repository Layer
    subgraph Repositories["Repository Layer"]
        UserRepo[User Repository]
        ListeningRepo[Listening Data Repository]
        ArtistRepo[Artist Repository]
        RecommendationRepo[Recommendation Repository]
        FeedbackRepo[Feedback Repository]
    end

    Database[(Application Database)]
    SpotifyAPI[(Spotify Web API)]

    %% User -> Controllers
    User --> AuthController
    User --> DiscoveryController
    User --> ArtistController
    User --> FeedbackController

    %% Controllers -> Services
    AuthController --> AuthService
    DiscoveryController --> DiscoveryService
    ArtistController --> MetadataService
    FeedbackController --> FeedbackService

    %% Service -> Service
    AuthService --> SpotifyService
    SpotifyService --> SpotifyAPI
    SpotifyService --> AnalysisService
    AnalysisService --> DiscoveryService
    DiscoveryService --> MetadataService
    DiscoveryService --> ExplainService
    FeedbackService --> DiscoveryService
    DiscoveryService --> NotificationService

    %% Services -> Repositories
    AuthService --> UserRepo
    AnalysisService --> ListeningRepo
    MetadataService --> ArtistRepo
    DiscoveryService --> RecommendationRepo
    FeedbackService --> FeedbackRepo

    %% Repositories -> Database
    UserRepo --> Database
    ListeningRepo --> Database
    ArtistRepo --> Database
    RecommendationRepo --> Database
    FeedbackRepo --> Databasegit 