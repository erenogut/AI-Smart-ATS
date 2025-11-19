# AI Smart ATS - CV Analysis System

This project is a desktop application that helps you find the best candidates for a job. It uses Artificial Intelligence (AI) to read CVs and compare them with a Job Description. It gives a score to every candidate and shows their skills in a chart.

# Key Features

**AI Scoring:** It compares the CV and Job Description to see how well they match.
**Skill Radar:** It creates a chart to show the candidate's skills (Backend, Frontend, AI, etc.).
**Auto-Extraction:** It automatically finds the candidate's name and email.
**Excel Export:** You can save the results to an Excel file easily.

# Technologies Used

**Python:** Main programming language.
**PyQt6:** For the desktop user interface.
**FastAPI:** For the backend server.
**Sentence-Transformers:** For AI and text analysis.
**Matplotlib & Pandas:** For charts and data handling.

## How to Install

1. Clone this project:
   ```bash
   git clone [https://github.com/erenogut/AI-Smart-ATS.git](https://github.com/erenogut/AI-Smart-ATS.git)
   cd AI-Smart-ATS

2. Install the necessary libraries:
    ```bash
    pip install -r requirements.txt
    ```

3. Start the Server (Backend) Open a terminal in the project folder and run:
    ```bash
    python -m uvicorn main:app --reload
    ```
    
4. Open the App (Frontend) Open a new terminal and run:
    ```bash
    python desktop_app.py
    ```

Developer: Eren Öğüt