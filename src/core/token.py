# src/core/token.py
import logging
from typing import List, Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import pandas as pd

from src.core.configuration.config import settings

logger = logging.getLogger(__name__)

class TokenValidator:
    def __init__(self):
        self.security = HTTPBearer()
        self.valid_tokens: Optional[List[str]] = None

    def load_tokens(self) -> List[str]:
        try:
            tokens_link = settings.TOKENS_LIST
            if not tokens_link:
                raise ValueError("Environment variable TOKENS_LIST is not set or empty.")

            logger.info(f"Loading tokens from: {tokens_link}")

            df = pd.read_csv(tokens_link, encoding='utf-8')
            logger.info(f"CSV content: {df.to_dict()}")
            
            valid_tokens = df.loc[df['source'] == settings.SERVICE_NAME, 'token'].tolist()
            logger.info(f"Valid tokens for {settings.SERVICE_NAME}: {valid_tokens}")

            if not valid_tokens:
                logger.warning(f"No valid tokens found for source: {settings.SERVICE_NAME}")
                # Покажем все уникальные значения source для отладки
                unique_sources = df['source'].unique().tolist() if 'source' in df.columns else []
                logger.warning(f"Available sources in CSV: {unique_sources}")

            logger.info("Tokens loaded successfully.")
            return valid_tokens
        except Exception as e:
            logger.error(f"Failed to load tokens: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="Internal server error - token validation failed."
            )

    async def __call__(self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
        if self.valid_tokens is None:
            self.valid_tokens = self.load_tokens()

        token = credentials.credentials
        logger.info(f"Checking token: {token[:10]}... against {len(self.valid_tokens)} valid tokens")
        
        if token not in self.valid_tokens:
            logger.warning(f"Unauthorized access attempt with token: {token[:10]}...")
            raise HTTPException(
                status_code=401,
                detail="Unauthorized.",
            )
        logger.info(f"Token verified successfully: {token[:10]}...")
        return token


token_validator = TokenValidator()