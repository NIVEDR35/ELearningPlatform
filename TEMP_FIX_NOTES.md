# Quick fix: Update course_detail.html to use lesson objects properly

The issue is that we're passing individual fields to playLesson() but we need the full lesson object.

## Solution:
1. Change onclick to pass lesson.id
2. Fetch full lesson data from API
3. Populate all tabs

This requires updating:
- The onclick handlers in the template (lines 44, 84)
- The playLesson JavaScript function
- Adding API endpoint to get lesson details

Due to the complexity, I'll create a simpler immediate fix by passing the lesson as JSON.
