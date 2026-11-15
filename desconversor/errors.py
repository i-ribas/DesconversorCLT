"""Erros com mensagem amigável, mostrada direto ao usuário."""


class AppError(Exception):
    """Erro com mensagem amigável para mostrar ao usuário."""


class ApiError(AppError):
    """Erro ao conversar com o ParaTranz."""
