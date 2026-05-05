"""
Sistema de Níveis — Progressão com Curva Crescente
===================================================

Fórmula base (sugestão do usuário):
    xp_necessario(level) = 100 * level * 1.2  →  120 * level

Isso define o CUSTO de cada nível (XP para sair do nível N e chegar ao N+1):
    Level 1 → 2 :   120 XP
    Level 2 → 3 :   240 XP
    Level 3 → 4 :   360 XP
    Level 5 → 6 :   600 XP
    Level 10 → 11: 1200 XP

XP ACUMULADO para atingir o nível L (soma aritmética):
    cumulative(L) = sum(120*i, i=1..L-1) = 60 * L * (L - 1)

INVERSA (nível a partir do XP total, sem loop):
    60L² - 60L - xp = 0
    L = 0.5 + sqrt(0.25 + xp / 60)
    level = floor(L)
"""
import math


def xp_threshold(level: int) -> int:
    """XP total acumulado necessário para ATINGIR o `level` (partindo do nível 1)."""
    if level <= 1:
        return 0
    return 60 * level * (level - 1)


def xp_cost_for_level(level: int) -> int:
    """XP necessário para sair do `level` atual e chegar ao próximo."""
    return 120 * level  # = 100 * level * 1.2


def calculate_level(xp: int) -> int:
    """
    Retorna o nível correspondente ao XP total acumulado.
    Derivado analiticamente da equação quadrática — sem loop.
    """
    if xp <= 0:
        return 1
    level = int(0.5 + math.sqrt(0.25 + xp / 60))
    return max(1, level)


def level_progress(xp: int) -> dict:
    """
    Retorna um dicionário com informações completas de progresso de nível.

    Exemplo (xp=500):
        level            = 3
        xp_current_level = 500 - 360 = 140   (XP dentro do nível atual)
        xp_to_next_level = 720 - 500  = 220   (XP faltando para o próximo)
        level_xp_cost    = 360                 (XP total do nível 3 → 4)
        progress_pct     = round(140/360*100)  (% de progresso no nível atual)
    """
    level = calculate_level(xp)
    threshold_current = xp_threshold(level)       # XP para entrar no nível atual
    threshold_next = xp_threshold(level + 1)      # XP para entrar no próximo nível
    cost = threshold_next - threshold_current     # = xp_cost_for_level(level)
    xp_in_level = xp - threshold_current
    xp_remaining = threshold_next - xp
    progress_pct = round(xp_in_level / cost * 100, 1) if cost > 0 else 100.0

    return {
        'level': level,
        'xp_current_level': xp_in_level,
        'xp_to_next_level': xp_remaining,
        'level_xp_cost': cost,
        'progress_pct': progress_pct,
    }
