from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import decode_access_token
from app.domain.models import User

security = HTTPBearer(auto_error=False)

def get_db() -> Generator[Session, None, None]:
    """Dependency for providing a SQLAlchemy database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Validates bearer JWT token and retrieves the current authenticated User model.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="សូមចូលប្រើប្រាស់ជាមុនសិន (Authentication required)",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token មិនត្រឹមត្រូវ ឬផុតកំណត់ (Invalid or expired token)",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token Payload មិនត្រឹមត្រូវ (Invalid token subject)",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = None
    if str(sub).isdigit():
        user = db.query(User).filter(User.id == int(sub)).first()
    else:
        user = db.query(User).filter(User.email == str(sub).strip().lower()).first()

    if not user and payload.get("email"):
        user = db.query(User).filter(User.email == str(payload.get("email")).strip().lower()).first()
    if not user and payload.get("user_id"):
        try:
            user = db.query(User).filter(User.id == int(payload.get("user_id"))).first()
        except Exception:
            pass

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="រកមិនឃើញគណនីនេះទេ (User not found)"
        )
    
    return user

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Ensures only users with role 'admin' can access."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ទំព័រនេះសម្រាប់តែអ្នកគ្រប់គ្រងប្រព័ន្ធ (Admin) ប៉ុណ្ណោះ"
        )
    return current_user

def require_teacher(current_user: User = Depends(get_current_user)) -> User:
    """Ensures only users with role 'teacher' or 'admin' can access."""
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ទំព័រនេះសម្រាប់តែគ្រូបង្រៀនប៉ុណ្ណោះ (Teacher access required)"
        )
    return current_user

def require_student(current_user: User = Depends(get_current_user)) -> User:
    """Ensures only users with role 'student' can access."""
    if current_user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ទំព័រនេះសម្រាប់តែសិស្សានុសិស្សប៉ុណ្ណោះ (Student access required)"
        )
    return current_user
