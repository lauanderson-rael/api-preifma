from datetime import date


def update_streak(user):
    """
    Atualiza o streak do usuário com base em last_study_date.
    Regras:
      - last_study_date == hoje  → não incrementa
      - last_study_date == ontem → incrementa +1
      - last_study_date < ontem  → reseta para 1
    Sempre atualiza last_study_date = hoje.
    Retorna o streak atualizado.
    """
    today = date.today()
    lsd = user.last_study_date

    if lsd is None:
        user.streak = 1
    elif lsd == today:
        pass  # já estudou hoje, sem mudança
    else:
        delta = (today - lsd).days
        if delta == 1:
            user.streak += 1
        else:
            user.streak = 1

    user.last_study_date = today
    user.save(update_fields=['streak', 'last_study_date'])
    return user.streak


def xp_per_correct(session_type: str) -> int:
    """Retorna XP por acerto conforme tipo de sessão."""
    return 15 if session_type == 'simulated' else 10
