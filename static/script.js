// Function to generate flashcards using Hugging Face
async function generateFlashcards() {
    const notes = document.getElementById('notesInput').value;
    
    if (!notes) {
        alert('Please enter some notes first!');
        return;
    }
    
    // Show loading message
    const flashcardsContainer = document.getElementById('flashcardsContainer');
    flashcardsContainer.innerHTML = '<div class="loading">Generating flashcards... This may take a moment.</div>';
    
    try {
        // Step 1: Send notes to Hugging Face API (via backend proxy for API key security)
        const hfResponse = await fetch('/api/generate', {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ notes })
        });

        if (!hfResponse.ok) {
            throw new Error("Hugging Face API error: " + hfResponse.status);
        }

        const hfData = await hfResponse.json();
        const generatedFlashcards = hfData.flashcards || [];

        // ADDED: A loop to save each flashcard to the database
        for (const card of generatedFlashcards) {
            // Step 2: Save each generated flashcard into backend
            const saveResponse = await fetch('/api/flashcards', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question: card.question,
                    answer: card.answer
                })
            });

            if (!saveResponse.ok) {
                // Log the error but continue to save other cards
                console.error('Error saving flashcard:', saveResponse.status);
            }
        }
        
        // Step 3: Reload flashcards to display all saved cards
        loadSavedFlashcards();

    } catch (error) {
        console.error('Error:', error);
        flashcardsContainer.innerHTML = '<div class="error">Sorry, something went wrong. Please try again.</div>';
    }
}

// Function to load saved flashcards
async function loadSavedFlashcards() {
    const flashcardsContainer = document.getElementById('flashcardsContainer');
    flashcardsContainer.innerHTML = '<div class="loading">Loading saved flashcards...</div>';
    
    try {
        const response = await fetch('/api/flashcards');
        
        if (!response.ok) {
            throw new Error('Server error: ' + response.status);
        }
        
        const flashcards = await response.json();
        
        // Display the flashcards
        displayFlashcards(flashcards);
    } catch (error) {
        console.error('Error:', error);
        flashcardsContainer.innerHTML = '<div class="error">Sorry, could not load saved flashcards.</div>';
    }
}

// Function to display flashcards
function displayFlashcards(flashcards) {
    const container = document.getElementById('flashcardsContainer');
    container.innerHTML = '';
    
    if (flashcards.length === 0) {
        container.innerHTML = '<div class="error">No flashcards found. Generate some first!</div>';
        return;
    }
    
    flashcards.forEach((card, index) => {
        const flashcardElement = document.createElement('div');
        flashcardElement.className = 'flashcard';
        flashcardElement.innerHTML = `
            <div class="flashcard-inner">
                <div class="flashcard-front">
                    <h3>Question ${index + 1}</h3>
                    <p>${card.question}</p>
                    <small>Click to see answer</small>
                </div>
                <div class="flashcard-back">
                    <p>${card.answer}</p>
                    <small>Click to see question</small>
                </div>
            </div>
        `;
        
        flashcardElement.addEventListener('click', function() {
            this.classList.toggle('flipped');
        });
        
        container.appendChild(flashcardElement);
    });
}

// =================== Payment functions ===================
let currentPlan = '';
let currentAmount = 0;

function initiatePayment(plan, amount) {
    currentPlan = plan;
    currentAmount = amount;
    const modal = document.getElementById('paymentModal');
    modal.style.display = 'block';
    
    // ADDED: Event listener for the Pay Now button
    document.getElementById('payNowBtn').onclick = () => loadIntaSendForm();
}

function closeModal() {
    const modal = document.getElementById('paymentModal');
    modal.style.display = 'none';
    document.getElementById('paymentForm').innerHTML = '';
}

async function loadIntaSendForm() {
    try {
        const phoneNumber = document.getElementById('phoneNumber').value;
        const email = document.getElementById('email').value;

        // FIXED: Add basic validation for phone number
        if (!phoneNumber) {
            document.getElementById('paymentForm').innerHTML = '<div class="error">Please enter a phone number.</div>';
            return;
        }

        const response = await fetch('/api/pay', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                plan: currentPlan, 
                amount: currentAmount, // Added amount to payload
                phone_number: phoneNumber,
                email: email
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to create payment session');
        }

        const data = await response.json();
        document.getElementById('paymentForm').innerHTML = 
            `<div class="payment-success">Payment request sent. Transaction ID: ${data.checkout?.invoice}</div>`;
        
        // ADDED: A small delay to show success message before closing modal
        setTimeout(() => {
            closeModal();
            alert("Payment request sent! Check your phone for a prompt.");
        }, 3000);

    } catch (error) {
        console.error('Error loading IntaSend form:', error);
        document.getElementById('paymentForm').innerHTML = 
            '<div class="payment-error">Failed to load payment form. Please try again.</div>';
    }
}