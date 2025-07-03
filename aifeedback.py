import csv

class AITutorFeedback:
    def __init__(self, student_name, courses_completed, total_questions, correct_answers, question_fit, challenge_success):
        self.student_name = student_name
        self.courses_completed = courses_completed
        self.total_questions = total_questions
        self.correct_answers = correct_answers
        self.question_fit = question_fit
        self.challenge_success = challenge_success

    def calculate_average_score(self):
        return round((self.correct_answers / self.total_questions) * 100, 2) if self.total_questions > 0 else 0

    def assess_course_progress(self):
        if self.courses_completed >= 5:
            return "You're progressing well! Keep exploring new topics to enhance your skills."
        elif self.courses_completed >= 3:
            return "Good effort! Completing more courses will strengthen your knowledge."
        else:
            return "Try to complete more courses. Regular learning will boost your skills."

    def assess_performance(self, avg_score):
        if avg_score >= 85:
            return "Excellent performance! You're understanding the concepts well. Keep up the great work!"
        elif avg_score >= 70:
            return "Good job! A little more practice will refine your skills further."
        elif avg_score >= 50:
            return "You're making progress, but reviewing tricky concepts will help."
        else:
            return "Your scores need improvement. Consider revisiting previous lessons and practicing more."

    def assess_question_fit(self):
        if self.question_fit >= 85:
            return "Great question selection! You are identifying the right topics effectively."
        elif self.question_fit >= 70:
            return "You're choosing questions well, but try to focus on areas where you struggle."
        else:
            return "You need to improve your question selection. Reviewing past mistakes will help."

    def assess_challenge_performance(self):
        return "You successfully completed the challenge on time! Keep pushing your limits." if self.challenge_success \
            else "Try to manage time better in challenges. Practice timed quizzes for improvement."

    def calculate_coins(self):
        return self.courses_completed * 2  # Fix: Remove unnecessary min() function

    def generate_feedback(self):
        avg_score = self.calculate_average_score()
        feedback = f"""
        Student Name: {self.student_name}
        ----------------------------------------
         Course Progress: {self.assess_course_progress()}
         Assessment Performance: {self.assess_performance(avg_score)}
         Marks:
           - Total Questions: {self.total_questions}
           - Correct Answers: {self.correct_answers}
           - Average Score: {avg_score}%
         Question Selection: {self.assess_question_fit()}
         Challenge Completion: {self.assess_challenge_performance()}
         Coins Earned: {self.calculate_coins()} coins
        ----------------------------------------
        """
        return feedback

# Read student data from CSV file and generate feedback for each student
with open("students.csv", newline="", encoding="utf-8") as file:
    reader = csv.DictReader(file)
    
    for row in reader:
        student_feedback = AITutorFeedback(
            student_name=row["student_name"],
            courses_completed=int(row["courses_completed"]),
            total_questions=int(row["total_questions"]),
            correct_answers=int(row["correct_answers"]),
            question_fit=int(row["question_fit"]),
            challenge_success=row["challenge_success"].strip().lower() in ["yes", "true", "1"]  # Improved handling
        )

        print(student_feedback.generate_feedback())
