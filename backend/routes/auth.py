"""
API эндпоинты для авторизации
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from database import get_db, Operator
from config import settings

router = APIRouter()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class Token(BaseModel):
    access_token: str
    token_type: str


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    department: str = "support"


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    department: str
    supervisor_mode: str


def create_access_token(data: dict):
    """Создать JWT токен"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Operator:
    """Получить текущего пользователя из токена"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    result = await db.execute(
        select(Operator).where(Operator.email == email)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
        
    return user


@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    """Регистрация нового оператора"""
    
    # Проверка существующего email
    result = await db.execute(
        select(Operator).where(Operator.email == user.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Email уже зарегистрирован"
        )
        
    # Создание оператора
    hashed_password = pwd_context.hash(user.password)
    
    # Генерация SIP extension
    result = await db.execute(select(Operator))
    operators_count = len(result.scalars().all())
    sip_extension = f"{100 + operators_count + 1}"
    
    new_operator = Operator(
        name=user.name,
        email=user.email,
        password_hash=hashed_password,
        department=user.department,
        sip_extension=sip_extension,
        sip_password=f"pass{sip_extension}"
    )
    
    db.add(new_operator)
    await db.commit()
    await db.refresh(new_operator)
    
    return UserResponse(
        id=new_operator.id,
        name=new_operator.name,
        email=new_operator.email,
        department=new_operator.department,
        supervisor_mode=new_operator.supervisor_mode
    )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Вход в систему"""
    
    result = await db.execute(
        select(Operator).where(Operator.email == form_data.username)
    )
    user = result.scalar_one_or_none()
    
    if not user or not pwd_context.verify(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token = create_access_token(data={"sub": user.email})
    
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: Operator = Depends(get_current_user)):
    """Получить информацию о текущем пользователе"""
    return UserResponse(
        id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        department=current_user.department,
        supervisor_mode=current_user.supervisor_mode
    )

