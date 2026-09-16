-- NRG SolarConnect — Store which Drive photos were used for the last
-- legacy social generation, so the app can actually show them.
-- Follows 0002-0081.
--
-- Owner: "no photos.. wahs the point of pointing the folder to a folder
-- which has pictures of hte installation" — generateLegacyPosts already
-- downloads real photos from the Drive folder to write the posts, but
-- nothing kept a record of which ones, so the card had no way to show
-- them back. One JSON array per project (fileId + mimeType), refreshed
-- on every generate — same "replace, not append" convention 0081 used
-- for generated_posts.

alter table legacy_social_projects
  add column generated_photo_ids jsonb;
