from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import User, get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/login")


class UserAuthSchema(BaseModel):
    username: str
    password: str


class AuthService:
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        # password hashing context lives on the service
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.secret_key = secret_key
        self.algorithm = algorithm

    def verify_password(
        self, plain_password: str, hashed_password: str
    ) -> bool:
        """Verify a plain password against a bcrypt hash."""
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Hash a plain password for storage."""
        return self.pwd_context.hash(password)

    def create_access_token(
        self, data: dict, expires_delta: timedelta | None = None
    ) -> str:
        """
        Create a signed JWT.
        Expect `data` to include {"sub": <username>} so we can recover it
        later.
        """
        to_encode = data.copy()

        expire = (
            datetime.utcnow() + expires_delta
            if expires_delta
            else datetime.utcnow() + timedelta(minutes=15)
        )
        to_encode.update({"exp": expire})

        encoded_jwt = jwt.encode(
            to_encode,
            self.secret_key,
            algorithm=self.algorithm,
        )
        return encoded_jwt

    def authenticate_user(
        self, db: Session, username: str, password: str
    ) -> User:
        """
        Look up user and validate password.
        Raise HTTP 401 if invalid.
        """
        user = db.query(User).filter(User.username == username).first()
        if not user or not self.verify_password(
            password, user.hashed_password
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user

    def get_current_user(
        self,
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db),
    ) -> User:
        """
        Decode the bearer token and return the current User.
        Raise HTTP 401 if token is invalid or user doesn't exist.
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
            )
            username: str | None = payload.get("sub")
            if username is None:
                raise credentials_exception
        except JWTError:
            # Covers bad signature, expired token, malformed, etc.
            raise credentials_exception

        user = db.query(User).filter(User.username == username).first()
        if user is None:
            raise credentials_exception

        return user


auth_service = AuthService(secret_key="1892dhianiandowqd0n")
