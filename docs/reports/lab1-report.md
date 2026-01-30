# Lab 1 – Design and Architecture Report

## Overview
This lab focused on designing the core data model and system architecture for our application. We explored entity relationships, monolithic architecture, modular monoliths, and microservices.

## ERD Ideation
We brainstormed the core entities required to support Spotify-based music discovery. Key entities include User, SpotifyAccount, ListeningHistoryItem, and Recommendation. Relationships were designed to reflect how Spotify data flows into the system and is transformed into recommendations.

AI was used to generate an initial ERD structure, which we refined by clarifying entity responsibilities and relationship cardinalities.

## Architecture Ideation
We identified major system responsibilities such as authentication, Spotify integration, data analysis, and recommendation delivery. Based on these responsibilities, we designed:

- A monolithic architecture for simplicity
- A modular monolith to improve separation of concerns
- A microservices architecture for scalability and independent deployment

AI was used to generate initial diagrams, which were iterated on to better reflect service boundaries and responsibilities.

## Iteration and Discussion
Throughout the design process, we refined entity definitions, clarified service boundaries, and added transparency-focused services to align with ethical recommendation goals.

## Conclusion
The final designs provide a strong foundation for implementation, supporting both early-stage development and future scalability.
