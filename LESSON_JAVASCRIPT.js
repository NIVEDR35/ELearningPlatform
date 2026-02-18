// Complete JavaScript for multi-modal lesson display

let currentLesson = null;

function toggleModule(index) {
    const content = document.getElementById(`module-${index}`);
    if (content.style.display === 'none') {
        content.style.display = 'block';
    } else {
        content.style.display = 'none';
    }
}

async function playLesson(lessonId) {
    try {
        // Fetch lesson details
        const response = await fetch(`/api/lessons/${lessonId}`);
        const lesson = await response.json();

        currentLesson = lesson;

        // Show modal
        const modal = document.getElementById('videoModal');
        modal.style.display = 'flex';

        // Set title
        document.getElementById('lessonTitle').innerText = lesson.title;

        // Populate video tab
        if (lesson.video_id) {
            document.getElementById('videoPlayer').src = `https://www.youtube.com/embed/${lesson.video_id}?autoplay=1`;
        }

        // Populate content tab
        document.getElementById('lessonContent').innerHTML = lesson.content || 'No content available.';

        // Show/hide and populate assignment tab
        if (lesson.assignment) {
            document.getElementById('tab-assignment').style.display = 'block';
            document.getElementById('lessonAssignment').innerHTML = lesson.assignment;
        } else {
            document.getElementById('tab-assignment').style.display = 'none';
        }

        // Show/hide and populate code tab
        if (lesson.code_example) {
            document.getElementById('tab-code').style.display = 'block';
            document.getElementById('lessonCode').textContent = lesson.code_example;
        } else {
            document.getElementById('tab-code').style.display = 'none';
        }

        // Show/hide and populate quiz tab
        if (lesson.quiz_questions && lesson.quiz_questions.length > 0) {
            document.getElementById('tab-quiz').style.display = 'block';
            displayQuiz(lesson.quiz_questions);
        } else {
            document.getElementById('tab-quiz').style.display = 'none';
        }

        // Show/hide and populate resources tab
        if (lesson.document_url || lesson.interactive_element) {
            document.getElementById('tab-resources').style.display = 'block';
            let resourcesHTML = '';
            if (lesson.document_url) {
                resourcesHTML += `<p><strong>📄 Recommended Reading:</strong><br>${lesson.document_url}</p>`;
            }
            document.getElementById('lessonResources').innerHTML = resourcesHTML;

            let interactiveHTML = '';
            if (lesson.interactive_element) {
                interactiveHTML += `<div style="background: #f0f9ff; padding: 15px; border-radius: 8px; border-left: 4px solid #3b82f6;"><h4 style="margin-top:0;">🎮 Interactive Challenge</h4><p>${lesson.interactive_element}</p></div>`;
            }
            document.getElementById('lessonInteractive').innerHTML = interactiveHTML;
        } else {
            document.getElementById('tab-resources').style.display = 'none';
        }

        // Track video watch
        if (lesson.video_id) {
            trackInteraction('VIDEO_WATCH', 'VIDEO', lesson.video_id, lesson.title);
        }

    } catch (error) {
        console.error('Error loading lesson:', error);
        alert('Failed to load lesson');
    }
}

function showTab(tabName) {
    // Hide all tabs
    const tabs = document.querySelectorAll('.tab-content');
    tabs.forEach(tab => tab.style.display = 'none');

    // Remove active class from all tab buttons
    const tabButtons = document.querySelectorAll('.lesson-tab');
    tabButtons.forEach(btn => btn.classList.remove('active'));

    // Show selected tab
    document.getElementById(`content-${tabName}`).style.display = 'block';
    document.getElementById(`tab-${tabName}`).classList.add('active');

    // Track interaction based on tab
    if (currentLesson) {
        if (tabName === 'content') {
            trackInteraction('DOCUMENT_READ', 'LESSON', currentLesson.id, currentLesson.title);
        } else if (tabName === 'code') {
            trackInteraction('CODE_EXAMPLE_VIEW', 'LESSON', currentLesson.id, currentLesson.title);
        } else if (tabName === 'resources') {
            trackInteraction('DOCUMENT_OPEN', 'LESSON', currentLesson.id, currentLesson.title);
        } else if (tabName === 'quiz') {
            // Track quiz viewing - contributes to Kinesthetic (K) and Reading (R)
            trackInteraction('QUIZ_ATTEMPT', 'QUIZ', currentLesson.id, currentLesson.title);
        } else if (tabName === 'assignment') {
            // Track assignment viewing - contributes to Kinesthetic (K) and Reading (R)
            trackInteraction('ASSIGNMENT_COMPLETE', 'ASSIGNMENT', currentLesson.id, currentLesson.title);
        }
    }
}

function displayQuiz(questions) {
    let html = '';
    questions.forEach((q, index) => {
        html += `
            <div style="background: var(--light); padding: 20px; border-radius: 12px; margin-bottom: 20px;">
                <h4 style="margin-top: 0;">Question ${index + 1}</h4>
                <p style="font-size: 16px; margin-bottom: 16px;">${q.question}</p>
                <div style="display: flex; flex-direction: column; gap: 10px;">
                    ${q.options.map((opt, optIndex) => `
                        <button class="quiz-option" onclick="checkAnswer(${index}, ${optIndex}, ${q.correct_answer}, '${q.explanation}')" 
                            style="padding: 12px; border: 2px solid var(--border); border-radius: 8px; background: white; text-align: left; cursor: pointer; transition: all 0.3s;">
                            ${String.fromCharCode(65 + optIndex)}. ${opt}
                        </button>
                    `).join('')}
                </div>
                <div id="quiz-feedback-${index}" style="margin-top: 12px;"></div>
            </div>
        `;
    });
    document.getElementById('lessonQuiz').innerHTML = html;
}

function checkAnswer(questionIndex, selectedOption, correctAnswer, explanation) {
    const feedback = document.getElementById(`quiz-feedback-${questionIndex}`);
    if (selectedOption === correctAnswer) {
        feedback.innerHTML = `<div style="background: #d1fae5; color: #065f46; padding: 12px; border-radius: 8px;">✅ Correct! ${explanation}</div>`;
    } else {
        feedback.innerHTML = `<div style="background: #fee2e2; color: #991b1b; padding: 12px; border-radius: 8px;">❌ Incorrect. ${explanation}</div>`;
    }

    // Track quiz attempt
    if (currentLesson) {
        trackInteraction('QUIZ_ATTEMPT', 'LESSON', currentLesson.id, currentLesson.title);
    }
}

function markAssignmentComplete() {
    if (currentLesson) {
        // Track with ASSIGNMENT resource type for proper VARK scoring (K+4, R+2)
        trackInteraction('ASSIGNMENT_COMPLETE', 'ASSIGNMENT', currentLesson.id, currentLesson.title);
        alert('Assignment marked as complete! Great job! 🎉');
    }
}

function copyCode() {
    const code = document.getElementById('lessonCode').textContent;
    navigator.clipboard.writeText(code).then(() => {
        alert('Code copied to clipboard!');
    });
}

function closeVideoModal() {
    const modal = document.getElementById('videoModal');
    modal.style.display = 'none';
    document.getElementById('videoPlayer').src = '';
    currentLesson = null;
}

function trackInteraction(interactionType, resourceType, resourceId, title) {
    fetch('/api/analytics/track', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            interaction_type: interactionType,
            resource_type: resourceType,
            resource_id: resourceId,
            duration: 60,
            metadata: { title: title }
        })
    }).then(res => res.json()).then(data => {
        console.log('Tracked:', interactionType, data);
    }).catch(err => console.error('Tracking error:', err));
}
