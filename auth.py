from datetime import datetime, timedelta
from jose import jwt, JWTError
import bcrypt
from dotenv import load_dotenv
import os
import re
import uuid
from sqlmodel import Session, select
from models import BlacklistedToken


load_dotenv()
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES'))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv('REFRESH_TOKEN_EXPIRE_DAYS'))
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

def verify_password(plain_password: str, hashed_password: str):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def verify_email(email: str):
    return True if re.search(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email) else False


def get_password_hash(password: str):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def create_access_token(data: dict):
    expire = datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = data.copy()
    to_encode.update({
        'exp': int(expire.timestamp()),
        'iat': int(datetime.now().timestamp()),
        'type': 'access',
        'jti': str(uuid.uuid4())
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict):
    expire = datetime.now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = data.copy()
    to_encode.update({
        'exp': int(expire.timestamp()),
        'iat': int(datetime.now().timestamp()),
        'type': 'refresh',
        'jti': str(uuid.uuid4())
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def is_access_token_expired(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get('type') != 'access':
            return True
        exp_timestamp = payload['exp']
        current_timestamp = datetime.now().timestamp()
        return exp_timestamp < current_timestamp
    except JWTError:
        return True


def is_refresh_token_expired(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get('type') != 'refresh':
            return True
        exp_timestamp = payload['exp']
        current_timestamp = datetime.now().timestamp()
        return exp_timestamp < current_timestamp
    except JWTError:
        return True


def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get('type') != 'access':
            return None
        return payload
    except JWTError:
        return None


def decode_refresh_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get('type') != 'refresh':
            return None
        return payload
    except JWTError:
        return None


def is_token_blacklisted(token: str, session: Session) -> bool:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_id = payload.get('jti')
        if not token_id:
            return True
        
        # Check if token is in blacklist
        blacklisted = session.exec(
            select(BlacklistedToken).where(BlacklistedToken.token_id == token_id)
        ).first()
        
        return blacklisted is not None
    except JWTError:
        return True


def blacklist_token(token: str, session: Session):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_id = payload.get('jti')
        exp_timestamp = payload.get('exp')
        
        if not token_id or not exp_timestamp:
            return False
        
        # Add token to blacklist
        blacklisted_token = BlacklistedToken(
            token_id=token_id,
            expires_at=datetime.fromtimestamp(exp_timestamp)
        )
        session.add(blacklisted_token)
        session.commit()
        return True
    except JWTError:
        return False