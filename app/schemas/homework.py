from typing import Optional, List
from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Homework CRUD
# ---------------------------------------------------------------------------

class CreateHomeworkRequest(BaseModel):
    class_id: int
    title: str
    subject: str
    description: Optional[str] = None
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    deadline: str
    # Set True to create a QCM homework (questions added separately)
    is_qcm: bool = False

class UpdateHomeworkRequest(BaseModel):
    title: Optional[str] = None
    subject: Optional[str] = None
    description: Optional[str] = None
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    deadline: Optional[str] = None


# ---------------------------------------------------------------------------
# File-upload submission
# ---------------------------------------------------------------------------

class SubmitHomeworkRequest(BaseModel):
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    student_note: Optional[str] = None

class GradeSubmissionRequest(BaseModel):
    score: float
    feedback: Optional[str] = None


# ---------------------------------------------------------------------------
# QCM — teacher creates questions
# ---------------------------------------------------------------------------

class QuestionCreate(BaseModel):
    question_text: str
    choices: List[str]
    correct_answer: int          # 0-based index into choices
    order_index: int = 0

    @field_validator("choices")
    @classmethod
    def at_least_two_choices(cls, v: List[str]) -> List[str]:
        if len(v) < 2:
            raise ValueError("សំណួរQCMត្រូវតែមានជម្រើសយ៉ាងតិច ២")
        return v

    @field_validator("correct_answer")
    @classmethod
    def valid_correct_answer(cls, v: int, info) -> int:
        choices = info.data.get("choices", [])
        if choices and not (0 <= v < len(choices)):
            raise ValueError("correct_answer ត្រូវតែជា index ដែលត្រឹមត្រូវក្នុង choices")
        return v

class BulkCreateQuestionsRequest(BaseModel):
    questions: List[QuestionCreate]


# ---------------------------------------------------------------------------
# QCM — response shapes
# ---------------------------------------------------------------------------

class QuestionOut(BaseModel):
    id: int
    homework_id: int
    question_text: str
    choices: List[str]
    order_index: int
    # correct_answer is intentionally omitted from student-facing responses

    class Config:
        from_attributes = True

class QuestionWithAnswerOut(QuestionOut):
    """Teacher-facing: includes correct answer."""
    correct_answer: int


# ---------------------------------------------------------------------------
# QCM — student submits answers
# ---------------------------------------------------------------------------

class AnswerItem(BaseModel):
    question_id: int
    chosen_answer: int           # 0-based index

class SubmitQCMRequest(BaseModel):
    answers: List[AnswerItem]
    student_note: Optional[str] = None


# ---------------------------------------------------------------------------
# QCM — result shapes
# ---------------------------------------------------------------------------

class AnswerResultItem(BaseModel):
    question_id: int
    question_text: str
    choices: List[str]
    chosen_answer: int
    correct_answer: int
    is_correct: bool

class QCMResultOut(BaseModel):
    submission_id: int
    homework_id: int
    total_questions: int
    correct_count: int
    score: float                 # percentage 0-100
    answers: List[AnswerResultItem]
