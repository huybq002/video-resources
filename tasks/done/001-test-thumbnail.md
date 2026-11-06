---
id: 001-test-thumbnail
priority: 1
status: done
---

# Test: 3 thumbnail variants

## Goal
Make 3 thumbnail variants (format: long-form 16:9, 1280x720) for a video titled "Nói tiếng Anh tự tin trong 7 ngày" (topic: practising English conversation with an AI partner).

## Inputs
No assets yet. Use text and shapes only. Use the html-thumbnail skill.

## Output
outputs/001-test-thumbnail/thumbnails/ (a/b/c .html and .png), rows appended to data/thumbnail-results.csv.

## Done when
- [x] 3 PNG files exist and were visually checked
- [x] 3 rows added to data/thumbnail-results.csv

## Progress notes
- Assumed long-form 1280x720. data/thumbnail-results.csv had no CTR data, so explored 3 different styles (navy+bubbles, yellow big number, red/green split).
- Fixed 5-word headlines to <=4 words after visual check. Variants follow contrast/focal-point/safe-margin principles; CTR must be measured after posting.
