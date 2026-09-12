from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from sqlalchemy.orm import Session
from app.core.dependencies import get_db, get_current_user, require_teacher, require_student
from app.domain.models import User, Homework, HomeworkQuestion, Submission, StudentAnswer, Enrollment
from app.schemas.homework import (
    CreateHomeworkRequest, UpdateHomeworkRequest,
    SubmitHomeworkRequest, GradeSubmissionRequest,
    BulkCreateQuestionsRequest, SubmitQCMRequest,
)
from app.domain.cloudinary_service import upload_file

router = APIRouter(prefix="/homework", tags=["Homework & Cloudinary Assignments"])


# ---------------------------------------------------------------------------
# File upload helper
# ---------------------------------------------------------------------------

@router.post("/upload")
async def upload_assignment_file(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    file_bytes = await file.read()
    res = upload_file(file_bytes, file.filename, folder="school_assignments")
    return {
        "success": True,
        "file_url": res["url"],
        "file_name": file.filename
    }


# ---------------------------------------------------------------------------
# List homeworks for a class
# ---------------------------------------------------------------------------

@router.get("/class/{class_id}")
def list_homeworks(class_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Homework).filter(Homework.class_id == class_id)
    if user.role == "teacher":
        query = query.filter(Homework.teacher_id == user.id)
    homeworks = query.order_by(Homework.created_at.desc()).all()

    total_students = db.query(Enrollment).filter(Enrollment.class_id == class_id).count()
    results = []

    for hw in homeworks:
        hw_dict = {
            "id": hw.id,
            "class_id": hw.class_id,
            "teacher_id": hw.teacher_id,
            "title": hw.title,
            "subject": hw.subject,
            "description": hw.description,
            "file_url": hw.file_url,
            "file_name": hw.file_name,
            "deadline": hw.deadline,
            "is_qcm": hw.is_qcm,
            "question_count": len(hw.questions) if hw.is_qcm else 0,
            "created_at": hw.created_at,
        }

        if user.role == "teacher":
            hw_dict["submissions_count"] = len(hw.submissions)
            hw_dict["submission_count"] = len(hw.submissions)
            hw_dict["total_students"] = total_students
        else:
            # Student view: include own submission status
            sub = next((s for s in hw.submissions if s.student_id == user.id), None)
            hw_dict["submission_id"] = sub.id if sub else None
            hw_dict["submitted_file"] = sub.file_url if sub else None
            hw_dict["submitted_at"] = sub.submitted_at.isoformat() if sub and sub.submitted_at else None
            hw_dict["score"] = float(sub.score) if sub and sub.score is not None else None
            hw_dict["feedback"] = sub.feedback if sub else None
            hw_dict["teacher_feedback"] = sub.feedback if sub else None

        results.append(hw_dict)

    return results


# ---------------------------------------------------------------------------
# Create homework (file-based or QCM)
# ---------------------------------------------------------------------------

@router.post("")
def create_homework(
    payload: CreateHomeworkRequest,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    school_class = db.query(SchoolClass).filter(SchoolClass.id == payload.class_id).first()
    if not school_class:
        raise HTTPException(status_code=404, detail="រកមិនឃើញថ្នាក់រៀននេះទេ")
    if teacher.role != "admin" and school_class.teacher_id != teacher.id:
        raise HTTPException(status_code=403, detail="អ្នកគ្មានសិទ្ធិបង្កើតកិច្ចការសម្រាប់ថ្នាក់របស់គ្រូផ្សេងទេ")

    new_hw = Homework(
        class_id=payload.class_id,
        teacher_id=teacher.id,
        title=payload.title,
        subject=payload.subject,
        description=payload.description,
        file_url=payload.file_url,
        file_name=payload.file_name,
        deadline=payload.deadline,
        is_qcm=payload.is_qcm,
    )
    db.add(new_hw)
    db.commit()
    db.refresh(new_hw)
    return {"success": True, "homework_id": new_hw.id, "is_qcm": new_hw.is_qcm}


# ---------------------------------------------------------------------------
# QCM — teacher adds questions (bulk)
# ---------------------------------------------------------------------------

@router.post("/{homework_id}/questions")
def create_questions(
    homework_id: int,
    payload: BulkCreateQuestionsRequest,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    hw = db.query(Homework).filter(Homework.id == homework_id).first()
    if not hw:
        raise HTTPException(status_code=404, detail="រកមិនឃើញកិច្ចការនេះទេ")
    if hw.teacher_id != teacher.id and teacher.role != "admin":
        raise HTTPException(status_code=403, detail="អ្នកគ្មានសិទ្ធិបន្ថែមសំណួរឱ្យកិច្ចការនេះទេ")
    if not hw.is_qcm:
        raise HTTPException(status_code=400, detail="កិច្ចការនេះមិនមែនជាប្រភេទ QCM ទេ")

    # Replace existing questions for idempotent re-saves
    db.query(HomeworkQuestion).filter(HomeworkQuestion.homework_id == homework_id).delete()

    for q in payload.questions:
        db.add(HomeworkQuestion(
            homework_id=homework_id,
            question_text=q.question_text,
            choices=q.choices,
            correct_answer=q.correct_answer,
            order_index=q.order_index,
        ))

    db.commit()
    return {"success": True, "question_count": len(payload.questions)}


# ---------------------------------------------------------------------------
# QCM — get questions (teacher gets correct answers, students don't)
# ---------------------------------------------------------------------------

@router.get("/{homework_id}/questions")
def get_questions(
    homework_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    hw = db.query(Homework).filter(Homework.id == homework_id).first()
    if not hw:
        raise HTTPException(status_code=404, detail="រកមិនឃើញកិច្ចការនេះទេ")
    if not hw.is_qcm:
        raise HTTPException(status_code=400, detail="កិច្ចការនេះមិនមែនជាប្រភេទ QCM ទេ")

    questions = (
        db.query(HomeworkQuestion)
        .filter(HomeworkQuestion.homework_id == homework_id)
        .order_by(HomeworkQuestion.order_index)
        .all()
    )

    if user.role == "teacher":
        return [
            {
                "id": q.id,
                "homework_id": q.homework_id,
                "question_text": q.question_text,
                "choices": q.choices,
                "correct_answer": q.correct_answer,
                "order_index": q.order_index,
            }
            for q in questions
        ]
    else:
        # Students do NOT see correct_answer
        return [
            {
                "id": q.id,
                "homework_id": q.homework_id,
                "question_text": q.question_text,
                "choices": q.choices,
                "order_index": q.order_index,
            }
            for q in questions
        ]


# ---------------------------------------------------------------------------
# QCM — student submits answers (auto-graded immediately)
# ---------------------------------------------------------------------------

@router.post("/{homework_id}/submit-qcm")
def submit_qcm(
    homework_id: int,
    payload: SubmitQCMRequest,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    hw = db.query(Homework).filter(Homework.id == homework_id).first()
    if not hw:
        raise HTTPException(status_code=404, detail="រកមិនឃើញកិច្ចការនេះទេ")
    if not hw.is_qcm:
        raise HTTPException(status_code=400, detail="កិច្ចការនេះមិនមែនជាប្រភេទ QCM ទេ")

    # Fetch all questions for this homework
    questions = {
        q.id: q
        for q in db.query(HomeworkQuestion).filter(HomeworkQuestion.homework_id == homework_id).all()
    }

    if not questions:
        raise HTTPException(status_code=400, detail="កិច្ចការ QCM នេះមិនទាន់មានសំណួរនៅឡើយទេ")

    # Validate that all submitted question_ids belong to this homework
    for ans in payload.answers:
        if ans.question_id not in questions:
            raise HTTPException(
                status_code=400,
                detail=f"question_id {ans.question_id} មិនស្ថិតក្នុងកិច្ចការនេះទេ",
            )

    # Validate that student hasn't submitted yet (single attempt only)
    submission = db.query(Submission).filter(
        Submission.homework_id == homework_id,
        Submission.student_id == student.id,
    ).first()

    if submission:
        raise HTTPException(
            status_code=400,
            detail="អ្នកបានធ្វើតេស្ត QCM នេះរួចរាល់ហើយ អាចធ្វើបានតែម្ដងគត់ (You have already completed this QCM quiz - 1 attempt only)",
        )

    submission = Submission(
        homework_id=homework_id,
        student_id=student.id,
        student_note=payload.student_note,
    )
    db.add(submission)
    db.flush()  # get submission.id

    # Persist each answer and count correct ones
    correct_count = 0
    answer_results = []

    for ans in payload.answers:
        q = questions[ans.question_id]
        is_correct = (ans.chosen_answer == q.correct_answer)
        if is_correct:
            correct_count += 1

        db.add(StudentAnswer(
            submission_id=submission.id,
            question_id=ans.question_id,
            chosen_answer=ans.chosen_answer,
            is_correct=is_correct,
        ))

        answer_results.append({
            "question_id": q.id,
            "question_text": q.question_text,
            "choices": q.choices,
            "chosen_answer": ans.chosen_answer,
            "correct_answer": q.correct_answer,
            "is_correct": is_correct,
        })

    # Auto-grade: score = percentage out of 100
    total = len(questions)
    auto_score = round((correct_count / total) * 100, 2) if total > 0 else 0.0

    submission.score = auto_score
    submission.graded_at = datetime.utcnow()
    submission.student_note = payload.student_note

    db.commit()

    return {
        "success": True,
        "submission_id": submission.id,
        "homework_id": homework_id,
        "total_questions": total,
        "correct_count": correct_count,
        "score": auto_score,
        "answers": answer_results,
    }


# ---------------------------------------------------------------------------
# QCM — student retrieves their own result
# ---------------------------------------------------------------------------

@router.get("/{homework_id}/my-qcm-result")
def get_my_qcm_result(
    homework_id: int,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    hw = db.query(Homework).filter(Homework.id == homework_id).first()
    if not hw:
        raise HTTPException(status_code=404, detail="រកមិនឃើញកិច្ចការនេះទេ")
    if not hw.is_qcm:
        raise HTTPException(status_code=400, detail="កិច្ចការនេះមិនមែនជាប្រភេទ QCM ទេ")

    sub = db.query(Submission).filter(
        Submission.homework_id == homework_id,
        Submission.student_id == student.id,
    ).first()

    if not sub:
        return {"submitted": False, "result": None}

    answers = (
        db.query(StudentAnswer)
        .filter(StudentAnswer.submission_id == sub.id)
        .all()
    )

    questions = {
        q.id: q
        for q in db.query(HomeworkQuestion).filter(HomeworkQuestion.homework_id == homework_id).all()
    }

    answer_results = []
    for a in answers:
        q = questions.get(a.question_id)
        if not q:
            continue
        answer_results.append({
            "question_id": q.id,
            "question_text": q.question_text,
            "choices": q.choices,
            "chosen_answer": a.chosen_answer,
            "correct_answer": q.correct_answer,
            "is_correct": a.is_correct,
        })

    correct_count = sum(1 for a in answer_results if a["is_correct"])

    return {
        "submitted": True,
        "result": {
            "submission_id": sub.id,
            "homework_id": homework_id,
            "total_questions": len(questions),
            "correct_count": correct_count,
            "score": float(sub.score) if sub.score is not None else 0.0,
            "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
            "answers": answer_results,
        },
    }


# ---------------------------------------------------------------------------
# Teacher — get all submissions for a homework (file or QCM)
# ---------------------------------------------------------------------------

@router.get("/{homework_id}/submissions")
def get_homework_submissions(
    homework_id: int,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    hw = db.query(Homework).filter(Homework.id == homework_id).first()
    if not hw:
        raise HTTPException(status_code=404, detail="រកមិនឃើញកិច្ចការនេះទេ")

    submissions = db.query(Submission).filter(Submission.homework_id == homework_id).all()

    results = []
    for s in submissions:
        student = s.student
        enrollment = db.query(Enrollment).filter(
            Enrollment.class_id == hw.class_id,
            Enrollment.student_id == s.student_id,
        ).first()

        row = {
            "id": s.id,
            "homework_id": s.homework_id,
            "student_id": s.student_id,
            "file_url": s.file_url,
            "file_name": s.file_name,
            "student_note": s.student_note,
            "score": float(s.score) if s.score is not None else None,
            "feedback": s.feedback,
            "teacher_feedback": s.feedback,
            "status": "Graded" if s.score is not None else "Pending",
            "submitted_at": s.submitted_at.strftime("%Y-%m-%d %H:%M") if s.submitted_at else "",
            "graded_at": s.graded_at.strftime("%Y-%m-%d %H:%M") if s.graded_at else "",
            "student_name": student.name if student else "",
            "student_code": student.student_code if student else "",
            "avatar_url": student.avatar_url if student else None,
            "roll_no": enrollment.roll_no if enrollment else None,
            "is_qcm": hw.is_qcm,
        }

        # For QCM submissions include per-question breakdown for the teacher
        if hw.is_qcm:
            answers = db.query(StudentAnswer).filter(StudentAnswer.submission_id == s.id).all()
            questions_map = {
                q.id: q for q in db.query(HomeworkQuestion)
                .filter(HomeworkQuestion.homework_id == homework_id).all()
            }
            row["qcm_answers"] = [
                {
                    "question_id": a.question_id,
                    "question_text": questions_map[a.question_id].question_text if a.question_id in questions_map else "",
                    "choices": questions_map[a.question_id].choices if a.question_id in questions_map else [],
                    "chosen_answer": a.chosen_answer,
                    "correct_answer": questions_map[a.question_id].correct_answer if a.question_id in questions_map else None,
                    "is_correct": a.is_correct,
                }
                for a in answers
            ]
            row["correct_count"] = sum(1 for a in answers if a.is_correct)
            row["total_questions"] = len(questions_map)

        results.append(row)

    return results


# ---------------------------------------------------------------------------
# File-based submission
# ---------------------------------------------------------------------------

@router.post("/{homework_id}/submit")
def submit_homework(
    homework_id: int,
    payload: SubmitHomeworkRequest,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    hw = db.query(Homework).filter(Homework.id == homework_id).first()
    if not hw:
        raise HTTPException(status_code=404, detail="រកមិនឃើញកិច្ចការនេះទេ")
    if hw.is_qcm:
        raise HTTPException(status_code=400, detail="កិច្ចការ QCM ត្រូវប្រើ endpoint /submit-qcm")

    submission = db.query(Submission).filter(
        Submission.homework_id == homework_id,
        Submission.student_id == student.id,
    ).first()

    if submission:
        raise HTTPException(
            status_code=400,
            detail="អ្នកបានប្រគល់កិច្ចការនេះរួចរាល់ហើយ អាចផ្ញើបានតែម្ដងគត់ (You have already submitted this assignment - 1 submission only)",
        )

    submission = Submission(
        homework_id=homework_id,
        student_id=student.id,
        file_url=payload.file_url,
        file_name=payload.file_name,
        student_note=payload.student_note,
    )
    db.add(submission)

    db.commit()
    return {"success": True, "message": "បានផ្ញើកិច្ចការទៅកាន់លោកគ្រូរួចរាល់ហើយ"}


# ---------------------------------------------------------------------------
# Update / Delete homework
# ---------------------------------------------------------------------------

@router.put("/{homework_id}")
def update_homework(
    homework_id: int,
    payload: UpdateHomeworkRequest,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    hw = db.query(Homework).filter(Homework.id == homework_id).first()
    if not hw:
        raise HTTPException(status_code=404, detail="រកមិនឃើញកិច្ចការនេះទេ")
    if hw.teacher_id != teacher.id and teacher.role != "admin":
        raise HTTPException(status_code=403, detail="អ្នកគ្មានសិទ្ធិកែប្រែកិច្ចការនេះទេ")

    if payload.title is not None:
        hw.title = payload.title.strip()
    if payload.subject is not None:
        hw.subject = payload.subject.strip()
    if payload.description is not None:
        hw.description = payload.description.strip()
    if payload.file_url is not None:
        hw.file_url = payload.file_url.strip() if payload.file_url.strip() else None
    if payload.file_name is not None:
        hw.file_name = payload.file_name.strip() if payload.file_name.strip() else None
    if payload.deadline is not None:
        hw.deadline = payload.deadline.strip()

    db.commit()
    db.refresh(hw)
    return {"success": True, "message": "បានកែប្រែកិច្ចការរួចរាល់", "homework_id": hw.id}


@router.delete("/{homework_id}")
def delete_homework(
    homework_id: int,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    hw = db.query(Homework).filter(Homework.id == homework_id).first()
    if not hw:
        raise HTTPException(status_code=404, detail="រកមិនឃើញកិច្ចការនេះទេ")
    if hw.teacher_id != teacher.id and teacher.role != "admin":
        raise HTTPException(status_code=403, detail="អ្នកគ្មានសិទ្ធិលុបកិច្ចការនេះទេ")

    db.delete(hw)
    db.commit()
    return {"success": True, "message": "បានលុបកិច្ចការរួចរាល់"}


# ---------------------------------------------------------------------------
# Student — get own file-submission details
# ---------------------------------------------------------------------------

@router.get("/{homework_id}/my-submission")
def get_my_submission(
    homework_id: int,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    hw = db.query(Homework).filter(Homework.id == homework_id).first()
    if not hw:
        raise HTTPException(status_code=404, detail="រកមិនឃើញកិច្ចការនេះទេ")

    sub = db.query(Submission).filter(
        Submission.homework_id == homework_id,
        Submission.student_id == student.id,
    ).first()

    if not sub:
        return {"homework_id": homework_id, "submitted": False, "submission": None}

    return {
        "homework_id": homework_id,
        "submitted": True,
        "submission": {
            "id": sub.id,
            "file_url": sub.file_url,
            "file_name": sub.file_name,
            "student_note": sub.student_note,
            "score": float(sub.score) if sub.score is not None else None,
            "feedback": sub.feedback,
            "submitted_at": sub.submitted_at,
            "graded_at": sub.graded_at,
        },
    }


# ---------------------------------------------------------------------------
# Teacher — manually grade a submission (file-based or override QCM score)
# ---------------------------------------------------------------------------

@router.post("/submissions/{submission_id}/grade")
def grade_submission(
    submission_id: int,
    payload: GradeSubmissionRequest,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="រកមិនឃើញការប្រគល់កិច្ចការនេះទេ")

    submission.score = payload.score
    submission.feedback = payload.feedback
    submission.graded_at = datetime.utcnow()
    db.commit()
    return {"success": True, "score": payload.score}
