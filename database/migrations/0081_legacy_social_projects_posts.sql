-- NRG SolarConnect — Store generated posts on legacy (pre-app) social projects
-- Follows 0002-0080.
--
-- Owner: "I could add a social media folder...but it is NOT doing
-- anything! It should be showing me samples of what it is going to be
-- post on insta, fb, linkedin, google my business... selecting from
-- the photos already in the folder...and use the information
-- provided."
--
-- legacy_social_projects (0078) captured the facts but never generated
-- or stored anything — this is where generateLegacyPosts (social/
-- actions.ts) writes its result. One JSON array per project (platform/
-- caption/hashtags), not a separate social_posts-style table: unlike a
-- real project's ongoing draft/posted workflow, these are just sample
-- captions read off a folder, shown inline on the same card.

alter table legacy_social_projects
  add column generated_posts jsonb,
  add column last_generated_at timestamptz;
